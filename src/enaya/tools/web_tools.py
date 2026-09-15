"""
Enaya Agent - Web Tools
web_search, web_extract.
Mirrors Hermes Agent's tools/web_tools.py exactly.
"""

from __future__ import annotations

import json
import os
from typing import Any

from enaya.tools.registry import registry


# =============================================================================
# web_search
# =============================================================================

WEB_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for information. Returns up to 10 results with titles, URLs, and descriptions.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query to look up on the web"},
                "limit": {"type": "integer", "description": "Maximum number of results to return (default: 10, max: 50)", "default": 10},
            },
            "required": ["query"],
        },
    },
}


def check_web_search_requirements() -> bool:
    return True


def web_search_tool(query: str, limit: int = 10) -> str:
    """Search the web using DuckDuckGo HTML scraping."""
    try:
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import quote_plus, urljoin

        # Use DuckDuckGo HTML
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for result in soup.select(".result__body")[:limit]:
            title_elem = result.select_one(".result__title")
            snippet_elem = result.select_one(".result__snippet")
            url_elem = result.select_one(".result__url")

            if title_elem:
                title = title_elem.get_text(strip=True)
                link = title_elem.find("a")
                href = link.get("href") if link else ""
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                results.append({
                    "title": title,
                    "url": href,
                    "description": snippet,
                })

        return json.dumps({"data": {"web": results}})

    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="web_search",
    toolset="core",
    schema=WEB_SEARCH_SCHEMA,
    handler=web_search_tool,
    check_fn=check_web_search_requirements,
)


# =============================================================================
# web_extract
# =============================================================================

WEB_EXTRACT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_extract",
        "description": "Extract content from web page URLs. Returns clean page content in markdown/text. Also works with PDF URLs.",
        "parameters": {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs to extract content from (max 5 URLs per call)",
                    "maxItems": 5,
                },
                "char_limit": {"type": "integer", "description": "Optional per-page character budget (default: 15000)", "default": 15000},
            },
            "required": ["urls"],
        },
    },
}


def check_web_extract_requirements() -> bool:
    return True


def web_extract_tool(urls: list[str], char_limit: int = 15000) -> str:
    """Extract content from URLs using requests + BeautifulSoup."""
    try:
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urlparse

        results = []

        for url in urls[:5]:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()

                content_type = response.headers.get("Content-Type", "")

                if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
                    # PDF extraction would need pdfplumber or similar
                    content = "[PDF extraction not implemented - install pdfplumber]"
                else:
                    soup = BeautifulSoup(response.text, "html.parser")

                    # Remove script/style elements
                    for elem in soup(["script", "style", "nav", "footer", "header", "aside"]):
                        elem.decompose()

                    # Get text
                    text = soup.get_text(separator="\n", strip=True)

                    # Truncate if needed
                    if len(text) > char_limit:
                        text = text[:char_limit // 2] + "\n\n[TRUNCATED]\n\n" + text[-char_limit // 2:]

                    content = text

                results.append({
                    "url": url,
                    "title": soup.title.string.strip() if soup.title else urlparse(url).netloc,
                    "content": content,
                    "error": None,
                })

            except Exception as e:
                results.append({
                    "url": url,
                    "title": "",
                    "content": "",
                    "error": str(e),
                })

        return json.dumps({"results": results})

    except Exception as e:
        return json.dumps({"error": str(e)})


registry.register(
    name="web_extract",
    toolset="core",
    schema=WEB_EXTRACT_SCHEMA,
    handler=web_extract_tool,
    check_fn=check_web_extract_requirements,
)