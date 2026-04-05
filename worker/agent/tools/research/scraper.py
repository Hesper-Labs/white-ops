"""Web scraping tool - extract structured data from web pages."""

import json
from typing import Any

from agent.tools.base import BaseTool


class WebScraperTool(BaseTool):
    name = "web_scraper"
    description = (
        "Scrape structured data from web pages. "
        "Extract tables, lists, product data, contact info, and more."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to scrape"},
            "extract": {
                "type": "string",
                "enum": ["tables", "links", "text", "images", "metadata", "all"],
            },
            "selector": {"type": "string", "description": "CSS selector to target specific elements"},
        },
        "required": ["url"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        url = kwargs["url"]
        extract = kwargs.get("extract", "all")

        from playwright.async_api import async_playwright

        async with await async_playwright().start() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)

            result: dict = {}

            if extract in ("tables", "all"):
                tables = await page.eval_on_selector_all(
                    "table",
                    """tables => tables.map(t => {
                        const rows = Array.from(t.querySelectorAll('tr'));
                        return rows.map(r =>
                            Array.from(r.querySelectorAll('td,th')).map(c => c.textContent.trim())
                        );
                    })""",
                )
                result["tables"] = tables

            if extract in ("links", "all"):
                links = await page.eval_on_selector_all(
                    "a[href]",
                    "els => els.slice(0,100).map(e => ({text: e.textContent.trim(), href: e.href}))",
                )
                result["links"] = [l for l in links if l.get("text")]

            if extract in ("text", "all"):
                from bs4 import BeautifulSoup

                content = await page.content()
                soup = BeautifulSoup(content, "lxml")
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                result["text"] = soup.get_text(separator="\n", strip=True)[:8000]

            if extract in ("images", "all"):
                images = await page.eval_on_selector_all(
                    "img[src]",
                    "els => els.slice(0,50).map(e => ({src: e.src, alt: e.alt || ''}))",
                )
                result["images"] = images

            if extract in ("metadata", "all"):
                meta = await page.evaluate("""() => ({
                    title: document.title,
                    description: document.querySelector('meta[name="description"]')?.content || '',
                    keywords: document.querySelector('meta[name="keywords"]')?.content || '',
                    author: document.querySelector('meta[name="author"]')?.content || '',
                    og_title: document.querySelector('meta[property="og:title"]')?.content || '',
                    og_image: document.querySelector('meta[property="og:image"]')?.content || '',
                })""")
                result["metadata"] = meta

            if kwargs.get("selector"):
                elements = await page.eval_on_selector_all(
                    kwargs["selector"],
                    "els => els.map(e => e.textContent.trim())",
                )
                result["selected"] = elements

            await browser.close()

        return json.dumps(result, ensure_ascii=False)
