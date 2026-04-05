"""Code review tool - review files, find bugs, and suggest improvements using LLM."""

import json
import os
from typing import Any

from agent.tools.base import BaseTool


class CodeReviewTool(BaseTool):
    name = "code_review"
    description = (
        "Perform AI-powered code review. Review files for quality, "
        "find potential bugs, and suggest improvements using LLM analysis."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["review_file", "find_bugs", "suggest_improvements"],
                "description": "The code review action to perform",
            },
            "file_path": {
                "type": "string",
                "description": "Path to the file to review",
            },
            "code": {
                "type": "string",
                "description": "Code snippet to review (alternative to file_path)",
            },
            "language": {
                "type": "string",
                "description": "Programming language (auto-detected from extension if file_path given)",
            },
            "focus": {
                "type": "string",
                "description": "Specific aspects to focus on (e.g., 'security', 'performance', 'readability')",
            },
        },
        "required": ["action"],
    }

    LANG_MAP = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript/React",
        ".jsx": "JavaScript/React",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".rb": "Ruby",
        ".php": "PHP",
        ".c": "C",
        ".cpp": "C++",
        ".cs": "C#",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".sh": "Shell/Bash",
        ".sql": "SQL",
        ".html": "HTML",
        ".css": "CSS",
    }

    def _detect_language(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        return self.LANG_MAP.get(ext, "Unknown")

    async def _get_code(self, kwargs: dict) -> tuple[str, str]:
        """Get code and language from kwargs. Returns (code, language)."""
        code = kwargs.get("code")
        file_path = kwargs.get("file_path")

        if not code and not file_path:
            raise ValueError("Either file_path or code is required")

        if file_path:
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                code = f.read()
            language = kwargs.get("language") or self._detect_language(file_path)
        else:
            language = kwargs.get("language", "Unknown")

        # Truncate very large files
        if len(code) > 15000:
            code = code[:15000] + "\n\n... [truncated - file too large for full review]"

        return code, language

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]

        try:
            code, language = await self._get_code(kwargs)
        except (ValueError, FileNotFoundError) as e:
            return json.dumps({"error": str(e)})

        try:
            from agent.llm.provider import LLMProvider

            llm = LLMProvider()

            if action == "review_file":
                return await self._review_file(llm, code, language, kwargs)
            elif action == "find_bugs":
                return await self._find_bugs(llm, code, language, kwargs)
            elif action == "suggest_improvements":
                return await self._suggest_improvements(llm, code, language, kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except Exception as e:
            return json.dumps({"error": f"Code review failed: {e}"})

    async def _review_file(self, llm: Any, code: str, language: str, kwargs: dict) -> str:
        focus = kwargs.get("focus", "")
        focus_instruction = f"\nFocus especially on: {focus}" if focus else ""

        system = (
            f"You are an expert code reviewer for {language}. "
            "Provide a structured code review with sections: "
            "1) Summary, 2) Issues Found (severity: critical/warning/info), "
            "3) Code Quality Score (1-10), 4) Key Recommendations. "
            f"Be specific with line references where possible.{focus_instruction}"
        )

        response = await llm.chat(
            system=system,
            messages=[{"role": "user", "content": f"Review this {language} code:\n\n```{language.lower()}\n{code}\n```"}],
            temperature=0.3,
        )

        return json.dumps({
            "action": "review_file",
            "language": language,
            "file": kwargs.get("file_path", "inline"),
            "review": response.get("content", "Review failed"),
        })

    async def _find_bugs(self, llm: Any, code: str, language: str, kwargs: dict) -> str:
        focus = kwargs.get("focus", "")
        focus_instruction = f"\nFocus especially on: {focus}" if focus else ""

        system = (
            f"You are a bug-finding specialist for {language}. "
            "Analyze the code for potential bugs, including: "
            "1) Logic errors, 2) Edge cases, 3) Null/undefined issues, "
            "4) Race conditions, 5) Security vulnerabilities, "
            "6) Memory leaks, 7) Error handling gaps. "
            "Format each bug as: [SEVERITY] Line X: Description. "
            f"If no bugs found, state the code looks correct.{focus_instruction}"
        )

        response = await llm.chat(
            system=system,
            messages=[{"role": "user", "content": f"Find bugs in this {language} code:\n\n```{language.lower()}\n{code}\n```"}],
            temperature=0.2,
        )

        return json.dumps({
            "action": "find_bugs",
            "language": language,
            "file": kwargs.get("file_path", "inline"),
            "analysis": response.get("content", "Analysis failed"),
        })

    async def _suggest_improvements(self, llm: Any, code: str, language: str, kwargs: dict) -> str:
        focus = kwargs.get("focus", "")
        focus_instruction = f"\nFocus especially on: {focus}" if focus else ""

        system = (
            f"You are a {language} optimization expert. "
            "Suggest concrete improvements for: "
            "1) Performance optimizations, 2) Code readability, "
            "3) Best practices and patterns, 4) Error handling, "
            "5) Type safety, 6) Testing recommendations. "
            "For each suggestion, show the current code and the improved version. "
            f"Prioritize by impact.{focus_instruction}"
        )

        response = await llm.chat(
            system=system,
            messages=[{"role": "user", "content": f"Suggest improvements for this {language} code:\n\n```{language.lower()}\n{code}\n```"}],
            temperature=0.4,
        )

        return json.dumps({
            "action": "suggest_improvements",
            "language": language,
            "file": kwargs.get("file_path", "inline"),
            "suggestions": response.get("content", "Suggestion generation failed"),
        })
