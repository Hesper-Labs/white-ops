"""RSS reader tool - fetch and parse RSS/Atom feeds."""

import xml.etree.ElementTree as ET
from typing import Any

import httpx

from agent.tools.base import BaseTool

# Common namespaces
NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


class RSSReaderTool(BaseTool):
    name = "rss_reader"
    description = (
        "Fetch and parse RSS/Atom feeds. Retrieve feed entries, "
        "list entry details, and search within feed content."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["fetch_feed", "list_entries", "search_feeds"],
                "description": "Action to perform.",
            },
            "url": {
                "type": "string",
                "description": "RSS/Atom feed URL.",
            },
            "urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Multiple feed URLs (for search_feeds).",
            },
            "query": {
                "type": "string",
                "description": "Search query (for search_feeds).",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum entries to return. Default 20.",
            },
        },
        "required": ["action"],
    }

    async def _fetch_xml(self, url: str) -> ET.Element:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "WhiteOps-RSSReader/1.0"})
            resp.raise_for_status()
            return ET.fromstring(resp.text)

    def _parse_rss(self, root: ET.Element) -> dict:
        """Parse RSS 2.0 feed."""
        channel = root.find("channel")
        if channel is None:
            return {"title": "", "entries": []}

        feed_title = (channel.findtext("title") or "").strip()
        feed_link = (channel.findtext("link") or "").strip()
        feed_desc = (channel.findtext("description") or "").strip()

        entries = []
        for item in channel.findall("item"):
            entry = {
                "title": (item.findtext("title") or "").strip(),
                "link": (item.findtext("link") or "").strip(),
                "description": (item.findtext("description") or "").strip()[:500],
                "pub_date": (item.findtext("pubDate") or "").strip(),
                "author": (item.findtext("dc:creator", namespaces=NAMESPACES) or item.findtext("author") or "").strip(),
                "guid": (item.findtext("guid") or "").strip(),
            }
            entries.append(entry)

        return {
            "title": feed_title,
            "link": feed_link,
            "description": feed_desc,
            "entries": entries,
        }

    def _parse_atom(self, root: ET.Element) -> dict:
        """Parse Atom feed."""
        ns = NAMESPACES["atom"]

        feed_title = (root.findtext(f"{{{ns}}}title") or "").strip()
        link_el = root.find(f"{{{ns}}}link[@rel='alternate']")
        if link_el is None:
            link_el = root.find(f"{{{ns}}}link")
        feed_link = link_el.get("href", "") if link_el is not None else ""

        entries = []
        for item in root.findall(f"{{{ns}}}entry"):
            link_el = item.find(f"{{{ns}}}link[@rel='alternate']")
            if link_el is None:
                link_el = item.find(f"{{{ns}}}link")

            summary = (item.findtext(f"{{{ns}}}summary") or item.findtext(f"{{{ns}}}content") or "").strip()

            author_el = item.find(f"{{{ns}}}author")
            author = ""
            if author_el is not None:
                author = (author_el.findtext(f"{{{ns}}}name") or "").strip()

            entry = {
                "title": (item.findtext(f"{{{ns}}}title") or "").strip(),
                "link": link_el.get("href", "") if link_el is not None else "",
                "description": summary[:500],
                "pub_date": (item.findtext(f"{{{ns}}}updated") or item.findtext(f"{{{ns}}}published") or "").strip(),
                "author": author,
                "guid": (item.findtext(f"{{{ns}}}id") or "").strip(),
            }
            entries.append(entry)

        return {"title": feed_title, "link": feed_link, "entries": entries}

    def _parse_feed(self, root: ET.Element) -> dict:
        """Detect feed type and parse."""
        tag = root.tag.lower()
        if "feed" in tag:
            return self._parse_atom(root)
        return self._parse_rss(root)

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        limit = kwargs.get("limit", 20)

        if action == "fetch_feed":
            url = kwargs.get("url")
            if not url:
                return {"error": "url is required."}
            try:
                root = await self._fetch_xml(url)
                feed = self._parse_feed(root)
                feed["entries"] = feed["entries"][:limit]
                feed["url"] = url
                feed["entry_count"] = len(feed["entries"])
                return feed
            except httpx.HTTPError as e:
                return {"error": f"Failed to fetch feed: {e}"}
            except ET.ParseError as e:
                return {"error": f"Failed to parse feed XML: {e}"}

        elif action == "list_entries":
            url = kwargs.get("url")
            if not url:
                return {"error": "url is required."}
            try:
                root = await self._fetch_xml(url)
                feed = self._parse_feed(root)
                entries = feed["entries"][:limit]
                return {
                    "feed_title": feed.get("title", ""),
                    "entries": entries,
                    "count": len(entries),
                }
            except (httpx.HTTPError, ET.ParseError) as e:
                return {"error": f"Failed: {e}"}

        elif action == "search_feeds":
            urls = kwargs.get("urls", [])
            query = kwargs.get("query", "").lower()
            if not urls:
                return {"error": "urls list is required."}
            if not query:
                return {"error": "query is required."}

            results = []
            errors = []
            for url in urls:
                try:
                    root = await self._fetch_xml(url)
                    feed = self._parse_feed(root)
                    for entry in feed["entries"]:
                        text = f"{entry.get('title', '')} {entry.get('description', '')}".lower()
                        if query in text:
                            entry["feed_title"] = feed.get("title", "")
                            entry["feed_url"] = url
                            results.append(entry)
                except Exception as e:
                    errors.append({"url": url, "error": str(e)})

            results = results[:limit]
            resp: dict[str, Any] = {"results": results, "count": len(results)}
            if errors:
                resp["errors"] = errors
            return resp

        return {"error": f"Unknown action: {action}"}
