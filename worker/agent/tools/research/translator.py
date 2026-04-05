"""Translation tool - translate text between languages using LLM."""

from typing import Any

from agent.tools.base import BaseTool


class TranslatorTool(BaseTool):
    name = "translator"
    description = (
        "Translate text between languages. Uses LLM for high-quality translations. "
        "Supports any language pair."
    )
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to translate"},
            "target_language": {"type": "string", "description": "Target language (e.g., 'Turkish', 'English', 'French')"},
            "source_language": {"type": "string", "description": "Source language (auto-detect if not specified)"},
        },
        "required": ["text", "target_language"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        from agent.llm.provider import LLMProvider

        text = kwargs["text"]
        target = kwargs["target_language"]
        source = kwargs.get("source_language", "auto-detect")

        llm = LLMProvider()
        response = await llm.chat(
            system=f"You are a professional translator. Translate the following text to {target}. Only output the translation, nothing else.",
            messages=[{"role": "user", "content": text}],
            temperature=0.3,
        )
        return response.get("content", "Translation failed")
