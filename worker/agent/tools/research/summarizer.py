"""Text summarizer tool - summarize text or URLs using LLM."""

import json
import re
from typing import Any

import httpx
import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024
MAX_INPUT_TEXT = 50000  # chars


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_BYTES:
        return text[:MAX_OUTPUT_BYTES] + "\n... [output truncated]"
    return text


class TextSummarizerTool(BaseTool):
    name = "text_summarizer"
    description = (
        "Summarize text content using the LLM. Supports direct text, URL-based "
        "summarization, and multi-text comparison across specified aspects."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["summarize", "summarize_url", "compare"],
                "description": "Summarization action to perform.",
            },
            "text": {
                "type": "string",
                "description": "Text to summarize (for summarize action).",
            },
            "url": {
                "type": "string",
                "description": "URL to fetch and summarize (for summarize_url action).",
            },
            "texts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of texts to compare (for compare action).",
            },
            "aspects": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Aspects to compare across texts (for compare action).",
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum summary length in words. Default: 200.",
            },
            "style": {
                "type": "string",
                "enum": ["bullet", "paragraph", "executive"],
                "description": "Summary style. Default: paragraph.",
            },
        },
        "required": ["action"],
    }

    async def _fetch_text_from_url(self, url: str) -> str:
        """Fetch and extract text content from a URL."""
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "WhiteOps-Summarizer/1.0"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        content = resp.text
        # Strip HTML tags
        content = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r"<[^>]+>", " ", content)
        content = re.sub(r"\s+", " ", content).strip()
        return content[:MAX_INPUT_TEXT]

    async def _call_llm(self, system: str, user_message: str) -> str:
        """Call the LLM provider for summarization."""
        try:
            from agent.llm.provider import LLMProvider

            llm = LLMProvider()
            result = await llm.chat(
                system=system,
                messages=[{"role": "user", "content": user_message}],
                temperature=0.3,
                max_tokens=2048,
            )
            return result.get("content", "")
        except ImportError:
            logger.warning("llm_provider_not_available")
            return "[Error: LLM provider not available. Install agent.llm.provider.]"
        except Exception as e:
            logger.error("llm_call_failed", error=str(e))
            return f"[Error: LLM call failed: {e}]"

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action")
        logger.info("summarizer_execute", action=action)

        try:
            if action == "summarize":
                return await self._summarize(kwargs)
            elif action == "summarize_url":
                return await self._summarize_url(kwargs)
            elif action == "compare":
                return await self._compare(kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except httpx.TimeoutException:
            return json.dumps({"error": "URL fetch timed out"})
        except httpx.HTTPStatusError as e:
            return json.dumps({"error": f"HTTP {e.response.status_code}"})
        except Exception as e:
            logger.error("summarizer_error", error=str(e))
            return json.dumps({"error": f"Summarization failed: {e}"})

    async def _summarize(self, kwargs: dict) -> str:
        text = kwargs.get("text", "")
        if not text:
            return json.dumps({"error": "text is required for summarize action"})

        text = text[:MAX_INPUT_TEXT]
        max_length = kwargs.get("max_length", 200)
        style = kwargs.get("style", "paragraph")

        style_instructions = {
            "bullet": "Present the summary as clear bullet points.",
            "paragraph": "Write the summary as coherent paragraphs.",
            "executive": (
                "Write an executive summary with key findings, implications, "
                "and recommended actions."
            ),
        }

        system = (
            "You are a precise summarizer. Summarize the given text accurately "
            "without adding information not present in the original. "
            f"Keep the summary under {max_length} words. "
            f"{style_instructions.get(style, style_instructions['paragraph'])}"
        )

        summary = await self._call_llm(system, f"Summarize:\n\n{text}")

        return _truncate(json.dumps({
            "summary": summary,
            "style": style,
            "original_length": len(text),
            "summary_length": len(summary),
        }))

    async def _summarize_url(self, kwargs: dict) -> str:
        url = kwargs.get("url", "")
        if not url:
            return json.dumps({"error": "url is required for summarize_url action"})

        text = await self._fetch_text_from_url(url)
        if not text.strip():
            return json.dumps({"error": "No text content found at URL"})

        # Delegate to _summarize with the fetched text
        kwargs["text"] = text
        kwargs["action"] = "summarize"
        result = await self._summarize(kwargs)

        # Inject source URL into the result
        try:
            data = json.loads(result)
            data["source_url"] = url
            return _truncate(json.dumps(data))
        except json.JSONDecodeError:
            return result

    async def _compare(self, kwargs: dict) -> str:
        texts = kwargs.get("texts", [])
        aspects = kwargs.get("aspects", [])

        if len(texts) < 2:
            return json.dumps({"error": "At least 2 texts are required for comparison"})
        if not aspects:
            return json.dumps({"error": "aspects list is required for comparison"})

        # Truncate each text
        truncated_texts = [t[:MAX_INPUT_TEXT // len(texts)] for t in texts]

        text_sections = "\n\n".join(
            f"--- TEXT {i + 1} ---\n{t}" for i, t in enumerate(truncated_texts)
        )

        system = (
            "You are a comparative analyst. Compare the given texts across "
            "the specified aspects. Be objective and thorough."
        )

        user_msg = (
            f"Compare the following {len(texts)} texts across these aspects: "
            f"{', '.join(aspects)}.\n\n{text_sections}"
        )

        comparison = await self._call_llm(system, user_msg)

        return _truncate(json.dumps({
            "comparison": comparison,
            "text_count": len(texts),
            "aspects": aspects,
        }))
