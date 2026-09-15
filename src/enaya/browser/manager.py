#!/usr/bin/env python3
"""
Enaya Agent - Browser Module
Browser automation with CDP, Browserbase, and agent-browser facade.
"""

from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Optional

from playwright.async_api import async_playwright, Browser, Page, BrowserContext


# =============================================================================
# Browser Provider Interface
# =============================================================================

class BrowserProvider(ABC):
    """Abstract browser provider."""
    
    @abstractmethod
    async def launch(self) -> None:
        """Launch browser."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close browser."""
        pass
    
    @abstractmethod
    async def new_page(self) -> Page:
        """Create new page."""
        pass
    
    @abstractmethod
    async def navigate(self, page: Page, url: str, wait_until: str = "networkidle") -> None:
        """Navigate to URL."""
        pass
    
    @abstractmethod
    async def screenshot(self, page: Page, path: str = None, full_page: bool = False) -> bytes:
        """Take screenshot."""
        pass
    
    @abstractmethod
    async def evaluate(self, page: Page, script: str) -> Any:
        """Evaluate JavaScript."""
        pass
    
    @abstractmethod
    async def click(self, page: Page, selector: str) -> None:
        """Click element."""
        pass
    
    @abstractmethod
    async def fill(self, page: Page, selector: str, value: str) -> None:
        """Fill input."""
        pass
    
    @abstractmethod
    async def wait_for_selector(self, page: Page, selector: str, timeout: int = 30000) -> None:
        """Wait for selector."""
        pass


# =============================================================================
# Local Playwright Provider
# =============================================================================

class LocalPlaywrightProvider(BrowserProvider):
    """Local Chromium/Firefox/WebKit via Playwright."""
    
    def __init__(self, browser_type: str = "chromium", headless: bool = True, args: list[str] = None):
        self.browser_type = browser_type
        self.headless = headless
        self.args = args or [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-extensions",
        ]
        self._playwright = None
        self._browser: Browser = None
        self._context: BrowserContext = None
    
    async def launch(self) -> None:
        self._playwright = await async_playwright().start()
        browser_launcher = getattr(self._playwright, self.browser_type)
        self._browser = await browser_launcher.launch(
            headless=self.headless,
            args=self.args,
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
    
    async def close(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
    
    async def new_page(self) -> Page:
        return await self._context.new_page()
    
    async def navigate(self, page: Page, url: str, wait_until: str = "networkidle") -> None:
        await page.goto(url, wait_until=wait_until, timeout=60000)
    
    async def screenshot(self, page: Page, path: str = None, full_page: bool = False) -> bytes:
        return await page.screenshot(path=path, full_page=full_page)
    
    async def evaluate(self, page: Page, script: str) -> Any:
        return await page.evaluate(script)
    
    async def click(self, page: Page, selector: str) -> None:
        await page.click(selector, timeout=30000)
    
    async def fill(self, page: Page, selector: str, value: str) -> None:
        await page.fill(selector, value, timeout=30000)
    
    async def wait_for_selector(self, page: Page, selector: str, timeout: int = 30000) -> None:
        await page.wait_for_selector(selector, timeout=timeout)


# =============================================================================
# Browserbase Cloud Provider
# =============================================================================

class BrowserbaseProvider(BrowserProvider):
    """Browserbase cloud browser provider."""
    
    def __init__(self, api_key: str = None, project_id: str = None, region: str = "us"):
        self.api_key = api_key or os.environ.get("BROWSERBASE_API_KEY")
        self.project_id = project_id or os.environ.get("BROWSERBASE_PROJECT_ID")
        self.region = region
        self._playwright = None
        self._browser: Browser = None
        self._context: BrowserContext = None
        self._session_id = None
    
    async def launch(self) -> None:
        if not self.api_key or not self.project_id:
            raise RuntimeError("BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID required")
        
        # Create session via Browserbase API
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.browserbase.com/v1/sessions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "projectId": self.project_id,
                    "region": self.region,
                    "browserSettings": {
                        "viewport": {"width": 1280, "height": 720},
                    },
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            session_data = resp.json()
            self._session_id = session_data["id"]
            connect_url = session_data["connectUrl"]
        
        # Connect via CDP
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.connect_over_cdp(connect_url)
        self._context = self._browser.contexts[0] if self._browser.contexts else await self._browser.new_context()
    
    async def close(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        
        # End session via API
        if self._session_id:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.delete(
                    f"https://api.browserbase.com/v1/sessions/{self._session_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
    
    async def new_page(self) -> Page:
        return await self._context.new_page()
    
    async def navigate(self, page: Page, url: str, wait_until: str = "networkidle") -> None:
        await page.goto(url, wait_until=wait_until, timeout=60000)
    
    async def screenshot(self, page: Page, path: str = None, full_page: bool = False) -> bytes:
        return await page.screenshot(path=path, full_page=full_page)
    
    async def evaluate(self, page: Page, script: str) -> Any:
        return await page.evaluate(script)
    
    async def click(self, page: Page, selector: str) -> None:
        await page.click(selector, timeout=30000)
    
    async def fill(self, page: Page, selector: str, value: str) -> None:
        await page.fill(selector, value, timeout=30000)
    
    async def wait_for_selector(self, page: Page, selector: str, timeout: int = 30000) -> None:
        await page.wait_for_selector(selector, timeout=timeout)


# =============================================================================
# Browser Manager
# =============================================================================

class BrowserManager:
    """Manages browser sessions and provides high-level operations."""
    
    def __init__(self, provider: BrowserProvider = None):
        self.provider = provider or LocalPlaywrightProvider()
        self._pages: dict[str, Page] = {}
    
    async def start(self) -> None:
        await self.provider.launch()
    
    async def stop(self) -> None:
        for page in self._pages.values():
            await page.close()
        self._pages.clear()
        await self.provider.close()
    
    async def get_page(self, page_id: str = "default") -> Page:
        if page_id not in self._pages:
            self._pages[page_id] = await self.provider.new_page()
        return self._pages[page_id]
    
    async def close_page(self, page_id: str) -> None:
        if page_id in self._pages:
            await self._pages[page_id].close()
            del self._pages[page_id]
    
    # High-level operations
    async def search_and_extract(self, query: str, max_results: int = 5) -> list[dict]:
        """Search web and extract content from top results."""
        page = await self.get_page()
        results = []
        
        # Use DuckDuckGo for search
        await self.provider.navigate(page, f"https://duckduckgo.com/html/?q={query}")
        await self.provider.wait_for_selector(page, ".result__body")
        
        # Extract results
        elements = await page.query_selector_all(".result__body")
        for i, elem in enumerate(elements[:max_results]):
            try:
                title_elem = await elem.query_selector(".result__title a")
                title = await title_elem.inner_text() if title_elem else ""
                link = await title_elem.get_attribute("href") if title_elem else ""
                snippet_elem = await elem.query_selector(".result__snippet")
                snippet = await snippet_elem.inner_text() if snippet_elem else ""
                
                results.append({
                    "title": title,
                    "url": link,
                    "snippet": snippet,
                })
            except:
                continue
        
        return results
    
    async def extract_page(self, url: str) -> dict:
        """Extract full content from a page."""
        page = await self.get_page()
        await self.provider.navigate(page, url)
        
        # Get title
        title = await page.title()
        
        # Extract main content
        content = await page.evaluate("""
            () => {
                // Remove scripts, styles, nav, footer
                const remove = document.querySelectorAll('script, style, nav, footer, header, aside, .ads, .advertisement');
                remove.forEach(el => el.remove());
                
                // Get main content
                const main = document.querySelector('main') || document.querySelector('article') || document.body;
                return main.innerText;
            }
        """)
        
        return {
            "url": url,
            "title": title,
            "content": content[:50000],  # Limit size
        }
    
    async def fill_form(self, url: str, fields: dict[str, str], submit_selector: str = None) -> dict:
        """Fill and optionally submit a form."""
        page = await self.get_page()
        await self.provider.navigate(page, url)
        
        for selector, value in fields.items():
            await self.provider.fill(page, selector, value)
        
        if submit_selector:
            await self.provider.click(page, submit_selector)
            await page.wait_for_load_state("networkidle")
        
        return {"success": True, "url": page.url}


# =============================================================================
# Browser Tool Integration
# =============================================================================

class BrowserTool:
    """Browser tool for agent integration."""
    
    def __init__(self, manager: BrowserManager = None):
        self.manager = manager or BrowserManager()
    
    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        """Search the web."""
        return await self.manager.search_and_extract(query, max_results)
    
    async def extract(self, url: str) -> dict:
        """Extract page content."""
        return await self.manager.extract_page(url)
    
    async def fill_form(self, url: str, fields: dict, submit: str = None) -> dict:
        """Fill a form."""
        return await self.manager.fill_form(url, fields, submit)
    
    async def screenshot(self, url: str = None, page_id: str = "default", full_page: bool = False) -> bytes:
        """Take screenshot."""
        page = await self.manager.get_page(page_id)
        if url:
            await self.manager.provider.navigate(page, url)
        return await self.manager.provider.screenshot(page, full_page=full_page)


# =============================================================================
# Browser Tool for Agent
# =============================================================================

BROWSER_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "browser",
        "description": "Control a web browser: search, navigate, extract, fill forms, screenshot",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "extract", "navigate", "screenshot", "fill_form"],
                    "description": "Action to perform",
                },
                "url": {"type": "string", "description": "URL for navigation/extraction"},
                "query": {"type": "string", "description": "Search query"},
                "fields": {"type": "object", "description": "Form fields (selector -> value)"},
                "submit_selector": {"type": "string", "description": "Submit button selector"},
                "page_id": {"type": "string", "description": "Page identifier", "default": "default"},
                "full_page": {"type": "boolean", "description": "Full page screenshot", "default": False},
            },
            "required": ["action"],
        },
    },
}


async def browser_tool(action: str, **kwargs) -> str:
    """Browser tool handler."""
    import json
    
    manager = BrowserManager()
    await manager.start()
    
    try:
        if action == "search":
            results = await manager.search_and_extract(kwargs.get("query", ""), kwargs.get("max_results", 5))
            return json.dumps({"results": results})
        
        elif action == "extract":
            url = kwargs.get("url")
            if not url:
                return json.dumps({"error": "url required"})
            result = await manager.extract_page(url)
            return json.dumps(result)
        
        elif action == "navigate":
            page = await manager.get_page(kwargs.get("page_id", "default"))
            await manager.provider.navigate(page, kwargs["url"])
            return json.dumps({"success": True, "url": page.url})
        
        elif action == "screenshot":
            page = await manager.get_page(kwargs.get("page_id", "default"))
            if kwargs.get("url"):
                await manager.provider.navigate(page, kwargs["url"])
            screenshot = await manager.provider.screenshot(page, full_page=kwargs.get("full_page", False))
            return json.dumps({"screenshot": screenshot.hex()})
        
        elif action == "fill_form":
            result = await manager.fill_form(
                kwargs["url"],
                kwargs.get("fields", {}),
                kwargs.get("submit_selector"),
            )
            return json.dumps(result)
        
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    
    finally:
        await manager.stop()