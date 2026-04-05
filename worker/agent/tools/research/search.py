"""Web search tool - search the web for information."""

import json
from typing import Any

from agent.tools.base import BaseTool


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Search the web for information using a search engine. "
        "Returns relevant search results with titles, URLs, and snippets."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "num_results": {"type": "integer", "description": "Number of results (default: 10)"},
        },
        "required": ["query"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        query = kwargs["query"]
        num_results = kwargs.get("num_results", 10)

        # Use the browser tool to search via DuckDuckGo (no API key needed)
        from playwright.async_api import async_playwright

        async with await async_playwright().start() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()

            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)

            results = await page.eval_on_selector_all(
                ".result",
                """elements => elements.map(el => ({
                    title: el.querySelector('.result__title')?.textContent?.trim() || '',
                    url: el.querySelector('.result__url')?.textContent?.trim() || '',
                    snippet: el.querySelector('.result__snippet')?.textContent?.trim() || '',
                }))""",
            )

            await browser.close()

        return json.dumps(results[:num_results])
