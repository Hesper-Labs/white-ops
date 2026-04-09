"""Web scraper tool - extract structured data from web pages using httpx + BeautifulSoup."""

import json
import re
import time
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024  # 50KB
MAX_PAGE_SIZE = 5 * 1024 * 1024  # 5MB
USER_AGENT = "WhiteOps-Scraper/1.0 (+https://whiteops.ai/bot)"

# Simple per-domain rate limiter
_last_request_time: dict[str, float] = {}


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_BYTES:
        return text[:MAX_OUTPUT_BYTES] + "\n... [output truncated]"
    return text


def _rate_limit(domain: str) -> None:
    """Enforce 1 request/second per domain."""
    now = time.monotonic()
    last = _last_request_time.get(domain, 0)
    wait = 1.0 - (now - last)
    if wait > 0:
        time.sleep(wait)
    _last_request_time[domain] = time.monotonic()


async def _check_robots(url: str) -> bool:
    """Check if the URL is allowed by robots.txt."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(robots_url)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
                return rp.can_fetch(USER_AGENT, url)
    except Exception:
        pass
    return True  # Allow if robots.txt is unreachable


class WebScraperTool(BaseTool):
    name = "web_scraper"
    description = (
        "Scrape and extract structured data from web pages. "
        "Supports CSS selector extraction, table parsing, link extraction, "
        "and full text extraction. Respects robots.txt and rate limits."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["scrape_page", "extract_table", "scrape_links", "scrape_text"],
                "description": "Scraping action to perform.",
            },
            "url": {
                "type": "string",
                "description": "URL of the page to scrape.",
            },
            "selectors": {
                "type": "object",
                "description": "CSS selectors mapping name -> selector (for scrape_page).",
                "additionalProperties": {"type": "string"},
            },
            "table_index": {
                "type": "integer",
                "description": "Index of the table to extract (0-based, for extract_table). Default: 0.",
            },
            "pattern": {
                "type": "string",
                "description": "Regex pattern to filter links (for scrape_links).",
            },
        },
        "required": ["action", "url"],
    }

    async def _fetch_page(self, url: str) -> str:
        """Fetch page HTML content with rate limiting and size check."""
        domain = urlparse(url).netloc
        _rate_limit(domain)

        # Check robots.txt
        allowed = await _check_robots(url)
        if not allowed:
            raise PermissionError(f"Blocked by robots.txt: {url}")

        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()

            content_length = int(resp.headers.get("content-length", 0))
            if content_length > MAX_PAGE_SIZE:
                raise ValueError(f"Page too large: {content_length} bytes (max {MAX_PAGE_SIZE})")

            text = resp.text
            if len(text.encode("utf-8")) > MAX_PAGE_SIZE:
                raise ValueError(f"Page content exceeds {MAX_PAGE_SIZE} bytes")

            return text

    def _parse_soup(self, html: str) -> Any:
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "html.parser")

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action")
        url = kwargs.get("url", "")
        logger.info("scraper_execute", action=action, url=url)

        if not url:
            return json.dumps({"error": "url is required"})

        try:
            if action == "scrape_page":
                return await self._scrape_page(url, kwargs)
            elif action == "extract_table":
                return await self._extract_table(url, kwargs)
            elif action == "scrape_links":
                return await self._scrape_links(url, kwargs)
            elif action == "scrape_text":
                return await self._scrape_text(url)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except PermissionError as e:
            logger.warning("scraper_robots_blocked", url=url)
            return json.dumps({"error": str(e)})
        except httpx.TimeoutException:
            logger.error("scraper_timeout", url=url)
            return json.dumps({"error": "Request timed out after 30 seconds"})
        except httpx.HTTPStatusError as e:
            return json.dumps({"error": f"HTTP {e.response.status_code} for {url}"})
        except Exception as e:
            logger.error("scraper_error", error=str(e))
            return json.dumps({"error": f"Scraping failed: {e}"})

    async def _scrape_page(self, url: str, kwargs: dict) -> str:
        selectors = kwargs.get("selectors", {})
        if not selectors:
            return json.dumps({"error": "selectors dict is required for scrape_page"})

        html = await self._fetch_page(url)
        soup = self._parse_soup(html)

        results: dict[str, Any] = {}
        for name, selector in selectors.items():
            elements = soup.select(selector)
            results[name] = [el.get_text(strip=True) for el in elements]

        logger.info("scraper_page_done", url=url, selector_count=len(selectors))
        return _truncate(json.dumps({"url": url, "results": results}))

    async def _extract_table(self, url: str, kwargs: dict) -> str:
        table_index = kwargs.get("table_index", 0)

        html = await self._fetch_page(url)
        soup = self._parse_soup(html)

        tables = soup.find_all("table")
        if not tables:
            return json.dumps({"error": "No tables found on page", "url": url})
        if table_index >= len(tables):
            return json.dumps({
                "error": f"Table index {table_index} out of range (found {len(tables)} tables)",
            })

        table = tables[table_index]
        rows = []
        headers: list[str] = []

        # Extract headers
        header_row = table.find("thead")
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]

        # Extract body rows
        tbody = table.find("tbody") or table
        for tr in tbody.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                if not headers and all(c for c in cells):
                    # Use first row as headers if no thead
                    headers = cells
                    continue
                rows.append(cells)

        result = {
            "url": url,
            "table_index": table_index,
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
        }
        logger.info("scraper_table_done", url=url, rows=len(rows))
        return _truncate(json.dumps(result))

    async def _scrape_links(self, url: str, kwargs: dict) -> str:
        pattern = kwargs.get("pattern")

        html = await self._fetch_page(url)
        soup = self._parse_soup(html)

        links = []
        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            text = a.get_text(strip=True)

            if pattern:
                if not re.search(pattern, href) and not re.search(pattern, text):
                    continue

            links.append({"text": text, "href": href})

        # Deduplicate by href
        seen: set[str] = set()
        unique_links = []
        for link in links:
            if link["href"] not in seen:
                seen.add(link["href"])
                unique_links.append(link)

        logger.info("scraper_links_done", url=url, count=len(unique_links))
        return _truncate(json.dumps({
            "url": url,
            "links": unique_links[:500],  # Cap at 500 links
            "count": len(unique_links),
        }))

    async def _scrape_text(self, url: str) -> str:
        html = await self._fetch_page(url)
        soup = self._parse_soup(html)

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        # Collapse excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        logger.info("scraper_text_done", url=url, length=len(text))
        return _truncate(json.dumps({
            "url": url,
            "text": text[:MAX_OUTPUT_BYTES],
            "length": len(text),
            "title": soup.title.string if soup.title else "",
        }))
