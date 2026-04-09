"""Translation tool - translate text using LibreTranslate or Google Translate API."""

import json
import os
from pathlib import Path
from typing import Any

import httpx
import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024


def _truncate(result: str) -> str:
    if len(result) > MAX_OUTPUT_BYTES:
        return result[:MAX_OUTPUT_BYTES] + "\n... [output truncated at 50KB]"
    return result


class TranslatorTool(BaseTool):
    name = "translator"
    description = (
        "Translate text between languages using LibreTranslate API (free) with "
        "fallback to Google Translate API. Supports translation, language detection, "
        "file translation, and listing supported languages. "
        "Env: TRANSLATE_API_URL (default: https://libretranslate.com), TRANSLATE_API_KEY."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["translate", "detect_language", "translate_file", "supported_languages"],
                "description": "Translation action to perform.",
            },
            "text": {
                "type": "string",
                "description": "Text to translate or detect language of.",
            },
            "target_lang": {
                "type": "string",
                "description": "Target language code (e.g., 'en', 'fr', 'de', 'es').",
            },
            "source_lang": {
                "type": "string",
                "description": "Source language code (auto-detect if not specified).",
            },
            "file_path": {
                "type": "string",
                "description": "Path to text file to translate (for translate_file).",
            },
        },
        "required": ["action"],
    }

    def _get_api_config(self) -> tuple[str, str]:
        """Get API URL and key from environment."""
        api_url = os.environ.get("TRANSLATE_API_URL", "https://libretranslate.com")
        api_key = os.environ.get("TRANSLATE_API_KEY", "")
        return api_url.rstrip("/"), api_key

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "")
        logger.info("translator_execute", action=action)

        api_url, api_key = self._get_api_config()

        try:
            if action == "translate":
                return await self._translate(kwargs, api_url, api_key)
            elif action == "detect_language":
                return await self._detect_language(kwargs, api_url, api_key)
            elif action == "translate_file":
                return await self._translate_file(kwargs, api_url, api_key)
            elif action == "supported_languages":
                return await self._supported_languages(api_url, api_key)
            else:
                return _truncate(json.dumps({"error": f"Unknown action: {action}"}))
        except httpx.HTTPError as e:
            logger.error("translator_api_error", action=action, error=str(e))
            return _truncate(json.dumps({"error": f"Translation API error: {e}"}))
        except Exception as e:
            logger.error("translator_error", action=action, error=str(e))
            return _truncate(json.dumps({"error": f"Translation failed: {e}"}))

    async def _translate(self, kwargs: dict, api_url: str, api_key: str) -> str:
        text = kwargs.get("text", "")
        target_lang = kwargs.get("target_lang", "")

        if not text:
            return _truncate(json.dumps({"error": "'text' is required"}))
        if not target_lang:
            return _truncate(json.dumps({"error": "'target_lang' is required"}))

        source_lang = kwargs.get("source_lang", "auto")

        payload: dict[str, Any] = {
            "q": text,
            "source": source_lang,
            "target": target_lang,
            "format": "text",
        }
        if api_key:
            payload["api_key"] = api_key

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{api_url}/translate", json=payload)
            resp.raise_for_status()
            data = resp.json()

        translated = data.get("translatedText", "")
        detected = data.get("detectedLanguage", {})

        logger.info("translator_translated", source=source_lang, target=target_lang, chars=len(text))
        return _truncate(json.dumps({
            "translated_text": translated,
            "source_lang": detected.get("language", source_lang),
            "target_lang": target_lang,
            "confidence": detected.get("confidence", None),
            "original_length": len(text),
            "translated_length": len(translated),
        }))

    async def _detect_language(self, kwargs: dict, api_url: str, api_key: str) -> str:
        text = kwargs.get("text", "")
        if not text:
            return _truncate(json.dumps({"error": "'text' is required"}))

        payload: dict[str, Any] = {"q": text}
        if api_key:
            payload["api_key"] = api_key

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{api_url}/detect", json=payload)
            resp.raise_for_status()
            data = resp.json()

        # LibreTranslate returns a list of detections
        detections = data if isinstance(data, list) else [data]

        logger.info("translator_detected", detections=len(detections))
        return _truncate(json.dumps({
            "detections": [
                {
                    "language": d.get("language", ""),
                    "confidence": d.get("confidence", 0),
                }
                for d in detections
            ],
        }))

    async def _translate_file(self, kwargs: dict, api_url: str, api_key: str) -> str:
        file_path = kwargs.get("file_path", "")
        target_lang = kwargs.get("target_lang", "")

        if not file_path:
            return _truncate(json.dumps({"error": "'file_path' is required"}))
        if not target_lang:
            return _truncate(json.dumps({"error": "'target_lang' is required"}))

        path = Path(file_path)
        if not path.exists():
            return _truncate(json.dumps({"error": f"File not found: {file_path}"}))

        # Check file size (max 1MB for translation)
        file_size = path.stat().st_size
        if file_size > 1_000_000:
            return _truncate(json.dumps({"error": "File too large. Maximum 1MB for file translation."}))

        text = path.read_text(encoding="utf-8")
        source_lang = kwargs.get("source_lang", "auto")

        # Translate in chunks if text is long
        max_chunk = 5000
        chunks = [text[i:i + max_chunk] for i in range(0, len(text), max_chunk)]
        translated_chunks = []

        async with httpx.AsyncClient(timeout=60) as client:
            for chunk in chunks:
                payload: dict[str, Any] = {
                    "q": chunk,
                    "source": source_lang,
                    "target": target_lang,
                    "format": "text",
                }
                if api_key:
                    payload["api_key"] = api_key

                resp = await client.post(f"{api_url}/translate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                translated_chunks.append(data.get("translatedText", ""))

        translated_text = "".join(translated_chunks)

        # Save translated file
        output_path = path.parent / f"{path.stem}_{target_lang}{path.suffix}"
        output_path.write_text(translated_text, encoding="utf-8")

        logger.info("translator_file_translated", file=file_path, target=target_lang, output=str(output_path))
        return _truncate(json.dumps({
            "success": True,
            "input_file": file_path,
            "output_file": str(output_path),
            "source_lang": source_lang,
            "target_lang": target_lang,
            "original_length": len(text),
            "translated_length": len(translated_text),
            "chunks_processed": len(chunks),
        }))

    async def _supported_languages(self, api_url: str, api_key: str) -> str:
        params = {}
        if api_key:
            params["api_key"] = api_key

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{api_url}/languages", params=params)
            resp.raise_for_status()
            data = resp.json()

        languages = [
            {"code": lang.get("code", ""), "name": lang.get("name", "")}
            for lang in data
        ]

        logger.info("translator_languages_listed", count=len(languages))
        return _truncate(json.dumps({
            "languages": languages,
            "count": len(languages),
        }))
