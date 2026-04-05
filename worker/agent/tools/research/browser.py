"""Web browser tool - browse websites using Playwright."""

import json
from typing import Any

from agent.tools.base import BaseTool


class BrowserTool(BaseTool):
    name = "browser"
    description = (
        "Browse the web using a real browser (Playwright/Chromium). "
        "Supports: navigating to URLs, reading page content, clicking elements, "
        "filling forms, taking screenshots, and extracting data."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["navigate", "read", "click", "fill", "screenshot", "extract_links", "extract_tables"],
            },
            "url": {"type": "string", "description": "URL to navigate to"},
            "selector": {"type": "string", "description": "CSS selector for interaction"},
            "text": {"type": "string", "description": "Text to type"},
            "output_path": {"type": "string", "description": "Path for screenshots"},
        },
        "required": ["action"],
    }

    def __init__(self) -> None:
        super().__init__()
        self._browser = None
        self._page = None

    async def _ensure_browser(self) -> None:
        if self._browser is None:
            from playwright.async_api import async_playwright
            pw = await async_playwright().start()
            self._browser = await pw.chromium.launch(headless=True)
            self._page = await self._browser.new_page()

    async def execute(self, **kwargs: Any) -> Any:
        await self._ensure_browser()
        action = kwargs["action"]

        if action == "navigate":
            url = kwargs.get("url", "")
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            title = await self._page.title()
            return json.dumps({"url": url, "title": title, "status": "loaded"})

        elif action == "read":
            content = await self._page.content()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "lxml")
            # Remove script/style
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            # Truncate to avoid token limits
            return text[:10000]

        elif action == "click":
            selector = kwargs.get("selector", "")
            await self._page.click(selector)
            return f"Clicked: {selector}"

        elif action == "fill":
            selector = kwargs.get("selector", "")
            text = kwargs.get("text", "")
            await self._page.fill(selector, text)
            return f"Filled {selector} with text"

        elif action == "screenshot":
            path = kwargs.get("output_path", "/tmp/screenshot.png")
            await self._page.screenshot(path=path, full_page=True)
            return f"Screenshot saved: {path}"

        elif action == "extract_links":
            links = await self._page.eval_on_selector_all(
                "a[href]",
                "elements => elements.map(e => ({text: e.textContent.trim(), href: e.href})).filter(l => l.text)",
            )
            return json.dumps(links[:50])

        elif action == "extract_tables":
            tables = await self._page.eval_on_selector_all(
                "table",
                """tables => tables.map(table => {
                    const rows = Array.from(table.querySelectorAll('tr'));
                    return rows.map(row => {
                        const cells = Array.from(row.querySelectorAll('td, th'));
                        return cells.map(cell => cell.textContent.trim());
                    });
                })""",
            )
            return json.dumps(tables)

        return f"Unknown action: {action}"
