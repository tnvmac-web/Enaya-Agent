#!/usr/bin/env python3
"""
Enaya Agent - Browser CDP Tool
Chrome DevTools Protocol based browser automation.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Optional

from enaya.tools.registry import registry


# =============================================================================
# Browser CDP Tool
# =============================================================================

BROWSER_CDP_SCHEMA = {
    "type": "function",
    "function": {
        "name": "browser_cdp",
        "description": "Control browser via Chrome DevTools Protocol (CDP). Allows fine-grained control over browser internals, network interception, console logs, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["connect", "navigate", "evaluate", "click", "type", "screenshot", "network_logs", "console_logs", "dom_snapshot", "close"],
                    "description": "Action to perform"
                },
                "url": {"type": "string", "description": "URL to navigate to"},
                "selector": {"type": "string", "description": "CSS selector for element interactions"},
                "text": {"type": "string", "description": "Text to type"},
                "script": {"type": "string", "description": "JavaScript to evaluate"},
                "cdp_endpoint": {"type": "string", "description": "CDP WebSocket endpoint (e.g., ws://localhost:9222/devtools/browser/...)"},
                "headless": {"type": "boolean", "description": "Run in headless mode", "default": True},
                "viewport": {"type": "object", "properties": {"width": {"type": "integer"}, "height": {"type": "integer"}}, "description": "Viewport dimensions"},
            },
            "required": ["action"],
        },
    },
}


def check_browser_cdp_requirements() -> bool:
    """Check if browser CDP requirements are met."""
    try:
        import playwright
        return True
    except ImportError:
        return False


class BrowserCDPManager:
    """Manages CDP connection and operations."""
    
    def __init__(self):
        self._browser = None
        self._context = None
        self._page = None
        self._cdp_session = None
        self._playwright = None
    
    async def connect(self, cdp_endpoint: str = None, headless: bool = True, viewport: dict = None) -> dict:
        """Connect to browser via CDP."""
        try:
            from playwright.async_api import async_playwright
            
            self._playwright = await async_playwright().start()
            
            if cdp_endpoint:
                # Connect to existing browser via CDP
                self._browser = await self._playwright.chromium.connect_over_cdp(cdp_endpoint)
            else:
                # Launch new browser with CDP enabled
                self._browser = await self._playwright.chromium.launch(
                    headless=headless,
                    args=["--remote-debugging-port=9222", "--no-sandbox", "--disable-dev-shm-usage"]
                )
            
            self._context = await self._browser.new_context(
                viewport=viewport or {"width": 1280, "height": 720}
            )
            self._page = await self._context.new_page()
            
            # Create CDP session for advanced operations
            self._cdp_session = await self._context.new_cdp_session(self._page)
            
            # Get CDP endpoint info
            cdp_url = "ws://localhost:9222" if not cdp_endpoint else cdp_endpoint
            
            return {
                "success": True,
                "cdp_endpoint": cdp_url,
                "message": "Connected to browser via CDP"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def navigate(self, url: str, wait_until: str = "networkidle") -> dict:
        """Navigate to URL."""
        try:
            if not self._page:
                return {"success": False, "error": "Not connected. Call connect first."}
            
            await self._page.goto(url, wait_until=wait_until, timeout=60000)
            return {"success": True, "url": self._page.url}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def evaluate(self, script: str) -> dict:
        """Evaluate JavaScript in page context."""
        try:
            if not self._page:
                return {"success": False, "error": "Not connected. Call connect first."}
            
            result = await self._page.evaluate(script)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def click(self, selector: str) -> dict:
        """Click element."""
        try:
            if not self._page:
                return {"success": False, "error": "Not connected. Call connect first."}
            
            await self._page.click(selector, timeout=30000)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def type(self, selector: str, text: str) -> dict:
        """Type text into element."""
        try:
            if not self._page:
                return {"success": False, "error": "Not connected. Call connect first."}
            
            await self._page.fill(selector, text, timeout=30000)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def screenshot(self, path: str = None, full_page: bool = False) -> dict:
        """Take screenshot."""
        try:
            if not self._page:
                return {"success": False, "error": "Not connected. Call connect first."}
            
            screenshot = await self._page.screenshot(path=path, full_page=full_page)
            if path:
                return {"success": True, "path": path}
            else:
                import base64
                return {"success": True, "screenshot_base64": base64.b64encode(screenshot).decode()}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_network_logs(self) -> dict:
        """Get network request/response logs."""
        try:
            if not self._cdp_session:
                return {"success": False, "error": "CDP session not available"}
            
            # Enable network domain
            await self._cdp_session.send("Network.enable")
            
            # Get request/response data
            # Note: This is simplified - real implementation would collect events
            return {"success": True, "message": "Network logging enabled. Use CDP events for full logs."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_console_logs(self) -> dict:
        """Get console logs."""
        try:
            if not self._cdp_session:
                return {"success": False, "error": "CDP session not available"}
            
            # Enable console domain
            await self._cdp_session.send("Console.enable")
            return {"success": True, "message": "Console logging enabled. Use CDP events for full logs."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_dom_snapshot(self) -> dict:
        """Get DOM snapshot."""
        try:
            if not self._page:
                return {"success": False, "error": "Not connected. Call connect first."}
            
            # Get DOM tree via CDP
            if self._cdp_session:
                result = await self._cdp_session.send("DOM.getDocument", {"depth": -1, "pierce": True})
                return {"success": True, "dom": result}
            else:
                # Fallback to page content
                content = await self._page.content()
                return {"success": True, "html": content}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def close(self) -> dict:
        """Close browser connection."""
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            return {"success": True, "message": "Browser closed"}
        except Exception as e:
            return {"success": False, "error": str(e)}


_browser_cdp_manager = BrowserCDPManager()


async def browser_cdp_tool(
    action: str,
    cdp_endpoint: str = None,
    url: str = None,
    selector: str = None,
    text: str = None,
    script: str = None,
    headless: bool = True,
    viewport: dict = None,
    path: str = None,
    full_page: bool = False,
) -> str:
    """Browser CDP tool handler."""
    import json
    import base64
    
    global _browser_cdp_manager
    
    try:
        if action == "connect":
            result = await _browser_cdp_manager.connect(cdp_endpoint, headless, viewport)
            return json.dumps(result)
        
        elif action == "navigate":
            if not url:
                return json.dumps({"error": "url required for navigate action"})
            result = await _browser_cdp_manager.navigate(url)
            return json.dumps(result)
        
        elif action == "evaluate":
            if not script:
                return json.dumps({"error": "script required for evaluate action"})
            result = await _browser_cdp_manager.evaluate(script)
            return json.dumps(result)
        
        elif action == "click":
            if not selector:
                return json.dumps({"error": "selector required for click action"})
            result = await _browser_cdp_manager.click(selector)
            return json.dumps(result)
        
        elif action == "type":
            if not selector or not text:
                return json.dumps({"error": "selector and text required for type action"})
            result = await _browser_cdp_manager.type(selector, text)
            return json.dumps(result)
        
        elif action == "screenshot":
            result = await _browser_cdp_manager.screenshot(path, full_page)
            # If screenshot returned as bytes, encode as base64
            if result.get("success") and "screenshot" not in result:
                # Already handled in method
                pass
            return json.dumps(result)
        
        elif action == "network_logs":
            result = await _browser_cdp_manager.get_network_logs()
            return json.dumps(result)
        
        elif action == "console_logs":
            result = await _browser_cdp_manager.get_console_logs()
            return json.dumps(result)
        
        elif action == "dom_snapshot":
            result = await _browser_cdp_manager.get_dom_snapshot()
            return json.dumps(result)
        
        elif action == "close":
            result = await _browser_cdp_manager.close()
            return json.dumps(result)
        
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    
    except Exception as e:
        return json.dumps({"error": str(e)})


def check_browser_cdp_requirements() -> bool:
    """Check if browser CDP requirements are met."""
    try:
        import playwright
        return True
    except ImportError:
        return False


registry.register(
    name="browser_cdp",
    toolset="browser",
    schema=BROWSER_CDP_SCHEMA,
    handler=browser_cdp_tool,
    check_fn=check_browser_cdp_requirements,
    is_async=True,
)