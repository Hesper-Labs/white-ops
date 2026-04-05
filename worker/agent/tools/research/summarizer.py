"""Summarizer tool - summarize text or web content using LLM."""

from typing import Any

import httpx

from agent.tools.base import BaseTool


class SummarizerTool(BaseTool):
    name = "summarizer"
    description = (
        "Summarize text or web page content. Provide either raw text or a URL. "
        "Uses the configured LLM to generate concise summaries."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["summarize"],
                "description": "Action to perform.",
            },
            "text": {
                "type": "string",
                "description": "Text to summarize.",
            },
            "url": {
                "type": "string",
                "description": "URL to fetch and summarize.",
            },
            "language": {
                "type": "string",
                "description": "Language for the summary (e.g., 'tr', 'en'). Default: same as input.",
            },
            "max_length": {
                "type": "string",
                "enum": ["short", "medium", "long"],
                "description": "Desired summary length. Default: medium.",
            },
        },
        "required": ["action"],
    }

    async def _fetch_text(self, url: str) -> str:
        """Fetch text content from a URL."""
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "WhiteOps-Summarizer/1.0"})
            resp.raise_for_status()
            content = resp.text

        # Simple HTML stripping
        import re
        # Remove script and style tags
        content = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", content, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        content = re.sub(r"<[^>]+>", " ", content)
        # Collapse whitespace
        content = re.sub(r"\s+", " ", content).strip()
        return content[:15000]  # Limit to avoid token overflow

    async def execute(self, **kwargs: Any) -> Any:
        from agent.llm.provider import LLMProvider

        text = kwargs.get("text", "")
        url = kwargs.get("url")
        language = kwargs.get("language", "")
        max_length = kwargs.get("max_length", "medium")

        if not text and not url:
            return {"error": "Provide either text or url to summarize."}

        if url and not text:
            try:
                text = await self._fetch_text(url)
            except httpx.HTTPError as e:
                return {"error": f"Failed to fetch URL: {e}"}

        if not text.strip():
            return {"error": "No text content found to summarize."}

        length_instruction = {
            "short": "Write a very concise summary in 2-3 sentences.",
            "medium": "Write a clear summary in 1-2 paragraphs.",
            "long": "Write a detailed summary covering all main points.",
        }.get(max_length, "Write a clear summary in 1-2 paragraphs.")

        lang_instruction = f" Write the summary in {language}." if language else ""

        system_prompt = (
            "You are a precise summarizer. Summarize the given text accurately "
            "without adding information not present in the original. "
            f"{length_instruction}{lang_instruction}"
        )

        try:
            llm = LLMProvider()
            result = await llm.chat(
                system=system_prompt,
                messages=[{"role": "user", "content": f"Summarize the following text:\n\n{text}"}],
                temperature=0.3,
                max_tokens=2048,
            )
            summary = result.get("content", "")
            return {
                "summary": summary,
                "source": url or "provided text",
                "original_length": len(text),
                "summary_length": len(summary),
            }
        except Exception as e:
            return {"error": f"LLM summarization failed: {e}"}
