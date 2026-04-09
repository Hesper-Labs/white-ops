"""RSS Feed tool - parse RSS/Atom feeds using feedparser and httpx."""

import json
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


class RSSFeedTool(BaseTool):
    name = "rss_feed"
    description = (
        "Parse and read RSS/Atom feeds. Fetch feed entries, get latest items, "
        "search across feeds, and create digests from multiple feeds."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["parse_feed", "get_latest", "search_feeds", "create_digest"],
                "description": "RSS action to perform.",
            },
            "url": {
                "type": "string",
                "description": "RSS/Atom feed URL (for parse_feed, get_latest, search_feeds).",
            },
            "urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Multiple feed URLs (for create_digest).",
            },
            "count": {
                "type": "integer",
                "description": "Number of entries to return (default 10).",
            },
            "query": {
                "type": "string",
                "description": "Search query string (for search_feeds).",
            },
            "max_per_feed": {
                "type": "integer",
                "description": "Max entries per feed for digest (default 5).",
            },
        },
        "required": ["action"],
    }

    async def _fetch_feed(self, url: str) -> dict:
        """Fetch and parse an RSS/Atom feed using feedparser."""
        try:
            import feedparser
        except ImportError:
            # Fallback to raw XML parsing if feedparser not available
            return await self._fetch_feed_raw(url)

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "WhiteOps-RSSFeed/1.0"},
            )
            resp.raise_for_status()

        feed = feedparser.parse(resp.text)

        entries = []
        for entry in feed.entries:
            entries.append({
                "title": getattr(entry, "title", ""),
                "link": getattr(entry, "link", ""),
                "published": getattr(entry, "published", getattr(entry, "updated", "")),
                "summary": (getattr(entry, "summary", "") or "")[:500],
                "author": getattr(entry, "author", ""),
            })

        return {
            "title": feed.feed.get("title", ""),
            "link": feed.feed.get("link", ""),
            "description": feed.feed.get("description", "")[:300],
            "entries": entries,
        }

    async def _fetch_feed_raw(self, url: str) -> dict:
        """Fallback XML parser when feedparser is not available."""
        import xml.etree.ElementTree as ET

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "WhiteOps-RSSFeed/1.0"},
            )
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        tag = root.tag.lower()

        entries = []
        if "feed" in tag:
            # Atom feed
            ns = "http://www.w3.org/2005/Atom"
            feed_title = (root.findtext(f"{{{ns}}}title") or "").strip()
            for item in root.findall(f"{{{ns}}}entry"):
                link_el = item.find(f"{{{ns}}}link[@rel='alternate']") or item.find(f"{{{ns}}}link")
                entries.append({
                    "title": (item.findtext(f"{{{ns}}}title") or "").strip(),
                    "link": link_el.get("href", "") if link_el is not None else "",
                    "published": (item.findtext(f"{{{ns}}}published") or item.findtext(f"{{{ns}}}updated") or "").strip(),
                    "summary": (item.findtext(f"{{{ns}}}summary") or "").strip()[:500],
                    "author": "",
                })
            return {"title": feed_title, "link": "", "description": "", "entries": entries}
        else:
            # RSS 2.0
            channel = root.find("channel")
            feed_title = (channel.findtext("title") or "").strip() if channel is not None else ""
            items = channel.findall("item") if channel is not None else []
            for item in items:
                entries.append({
                    "title": (item.findtext("title") or "").strip(),
                    "link": (item.findtext("link") or "").strip(),
                    "published": (item.findtext("pubDate") or "").strip(),
                    "summary": (item.findtext("description") or "").strip()[:500],
                    "author": (item.findtext("author") or "").strip(),
                })
            return {"title": feed_title, "link": "", "description": "", "entries": entries}

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "")
        logger.info("rss_feed_execute", action=action)

        if action == "parse_feed":
            url = kwargs.get("url", "")
            if not url:
                return _truncate(json.dumps({"error": "'url' is required"}))

            try:
                feed = await self._fetch_feed(url)
                feed["url"] = url
                feed["entry_count"] = len(feed["entries"])
                logger.info("rss_feed_parsed", url=url, entries=len(feed["entries"]))
                return _truncate(json.dumps(feed))
            except httpx.HTTPError as e:
                logger.error("rss_fetch_failed", url=url, error=str(e))
                return _truncate(json.dumps({"error": f"Failed to fetch feed: {e}"}))
            except Exception as e:
                logger.error("rss_parse_failed", url=url, error=str(e))
                return _truncate(json.dumps({"error": f"Failed to parse feed: {e}"}))

        elif action == "get_latest":
            url = kwargs.get("url", "")
            count = kwargs.get("count", 10)

            if not url:
                return _truncate(json.dumps({"error": "'url' is required"}))

            try:
                feed = await self._fetch_feed(url)
                entries = feed["entries"][:count]
                logger.info("rss_get_latest", url=url, count=len(entries))
                return _truncate(json.dumps({
                    "feed_title": feed.get("title", ""),
                    "entries": entries,
                    "count": len(entries),
                }))
            except Exception as e:
                logger.error("rss_get_latest_failed", url=url, error=str(e))
                return _truncate(json.dumps({"error": f"Failed to get latest entries: {e}"}))

        elif action == "search_feeds":
            url = kwargs.get("url", "")
            query = kwargs.get("query", "").lower()

            if not url:
                return _truncate(json.dumps({"error": "'url' is required"}))
            if not query:
                return _truncate(json.dumps({"error": "'query' is required"}))

            try:
                feed = await self._fetch_feed(url)
                results = []
                for entry in feed["entries"]:
                    text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
                    if query in text:
                        entry["feed_title"] = feed.get("title", "")
                        results.append(entry)

                logger.info("rss_search", url=url, query=query, results=len(results))
                return _truncate(json.dumps({
                    "query": query,
                    "results": results,
                    "count": len(results),
                }))
            except Exception as e:
                logger.error("rss_search_failed", url=url, error=str(e))
                return _truncate(json.dumps({"error": f"Feed search failed: {e}"}))

        elif action == "create_digest":
            urls = kwargs.get("urls", [])
            max_per_feed = kwargs.get("max_per_feed", 5)

            if not urls:
                return _truncate(json.dumps({"error": "'urls' list is required"}))

            digest = []
            errors = []

            for url in urls:
                try:
                    feed = await self._fetch_feed(url)
                    digest.append({
                        "feed_title": feed.get("title", url),
                        "feed_url": url,
                        "entries": feed["entries"][:max_per_feed],
                        "total_available": len(feed["entries"]),
                    })
                except Exception as e:
                    errors.append({"url": url, "error": str(e)})

            logger.info("rss_digest_created", feeds=len(digest), errors=len(errors))
            result: dict[str, Any] = {
                "digest": digest,
                "feeds_processed": len(digest),
                "total_entries": sum(len(d["entries"]) for d in digest),
            }
            if errors:
                result["errors"] = errors
            return _truncate(json.dumps(result))

        return _truncate(json.dumps({"error": f"Unknown action: {action}"}))
