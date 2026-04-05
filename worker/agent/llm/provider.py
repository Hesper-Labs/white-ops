"""LLM provider - unified interface for multiple LLM backends via LiteLLM."""

import json

import litellm
import structlog

from agent.config import settings

logger = structlog.get_logger()

# LiteLLM model name mapping
PROVIDER_MODEL_MAP = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
    "google": "gemini/gemini-2.0-flash",
    "ollama": "ollama/llama3.2",
}


class LLMProvider:
    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        self.provider = provider or settings.default_llm_provider
        self.model = model or settings.default_llm_model

        # Configure API keys
        if settings.anthropic_api_key:
            litellm.api_key = settings.anthropic_api_key
        if settings.openai_api_key:
            litellm.openai_key = settings.openai_api_key

    def _get_model_name(self) -> str:
        """Get the LiteLLM model name."""
        if self.provider == "ollama":
            return f"ollama/{self.model}"
        if self.provider == "google":
            return f"gemini/{self.model}"
        return self.model

    async def chat(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict:
        """Send a chat completion request."""
        full_messages = [{"role": "system", "content": system}] + messages

        kwargs: dict = {
            "model": self._get_model_name(),
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            kwargs["tools"] = tools

        if self.provider == "ollama":
            kwargs["api_base"] = settings.ollama_base_url

        try:
            response = await litellm.acompletion(**kwargs)
            choice = response.choices[0]
            message = choice.message

            result: dict = {"content": message.content or ""}

            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": json.loads(tc.function.arguments)
                            if isinstance(tc.function.arguments, str)
                            else tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]

            return result

        except Exception as e:
            logger.error("llm_error", provider=self.provider, model=self.model, error=str(e))
            raise
