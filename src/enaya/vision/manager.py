#!/usr/bin/env python3
"""
Enaya Agent - Vision Module
Multimodal vision analysis with clipboard support.
"""

from __future__ import annotations

import base64
import io
import os
from abc import ABC, abstractmethod

from PIL import Image

# =============================================================================
# Vision Provider Interface
# =============================================================================

class VisionProvider(ABC):
    """Abstract vision provider."""

    @abstractmethod
    async def analyze(self, image: Image.Image, prompt: str = "Describe this image in detail.") -> str:
        """Analyze image with prompt."""
        pass

    @abstractmethod
    async def extract_text(self, image: Image.Image) -> str:
        """Extract text from image (OCR)."""
        pass

    @abstractmethod
    async def answer_question(self, image: Image.Image, question: str) -> str:
        """Answer question about image."""
        pass


# =============================================================================
# OpenAI Vision Provider
# =============================================================================

class OpenAIVision(VisionProvider):
    """OpenAI GPT-4 Vision provider."""

    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.model = model

    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL image to base64."""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

    async def analyze(self, image: Image.Image, prompt: str = "Describe this image in detail.") -> str:
        b64_image = self._image_to_base64(image)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_image}",
                            },
                        },
                    ],
                }
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content

    async def extract_text(self, image: Image.Image) -> str:
        return await self.analyze(image, "Extract all text from this image. Return only the text content.")

    async def answer_question(self, image: Image.Image, question: str) -> str:
        return await self.analyze(image, question)


# =============================================================================
# Anthropic Vision Provider
# =============================================================================

class AnthropicVision(VisionProvider):
    """Anthropic Claude Vision provider."""

    def __init__(self, api_key: str = None, model: str = "claude-3-5-sonnet-20241022"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_TOKEN"))
        self.model = model

    def _image_to_base64(self, image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

    async def analyze(self, image: Image.Image, prompt: str = "Describe this image in detail.") -> str:
        b64_image = self._image_to_base64(image)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": b64_image,
                            },
                        },
                    ],
                }
            ],
        )
        return response.content[0].text

    async def extract_text(self, image: Image.Image) -> str:
        return await self.analyze(image, "Extract all text from this image. Return only the text content.")

    async def answer_question(self, image: Image.Image, question: str) -> str:
        return await self.analyze(image, question)


# =============================================================================
# Local Vision (using CLIP/other models)
# =============================================================================

class LocalVision(VisionProvider):
    """Local vision using CLIP/transformers."""

    def __init__(self, model_name: str = "openai/clip-vit-large-patch14"):
        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = CLIPModel.from_pretrained(model_name).to(self.device)
            self.processor = CLIPProcessor.from_pretrained(model_name)
            self.torch = torch
        except ImportError:
            raise RuntimeError("transformers not installed. Run: pip install transformers torch")

    async def analyze(self, image: Image.Image, prompt: str = "Describe this image in detail.") -> str:
        # CLIP is for classification, not generation
        # This is a placeholder - real implementation would use a generative model
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with self.torch.no_grad():
            outputs = self.model.get_image_features(**inputs)

        return f"[Local Vision] Image analyzed with CLIP. Features extracted: {outputs.shape}"

    async def extract_text(self, image: Image.Image) -> str:
        # Would need OCR model like Tesseract or Donut
        return "[Local Vision] OCR not implemented. Install pytesseract for OCR support."

    async def answer_question(self, image: Image.Image, question: str) -> str:
        return await self.analyze(image, question)


# =============================================================================
# Vision Manager
# =============================================================================

class VisionManager:
    """Manages vision analysis across providers."""

    def __init__(self):
        self.provider: VisionProvider | None = None
        self._clipboard_image: Image.Image | None = None

    def set_provider(self, provider: VisionProvider) -> None:
        self.provider = provider

    def auto_configure(self) -> None:
        """Auto-configure based on available API keys."""
        if os.environ.get("OPENAI_API_KEY"):
            self.provider = OpenAIVision()
        elif os.environ.get("ANTHROPIC_TOKEN"):
            self.provider = AnthropicVision()
        else:
            try:
                self.provider = LocalVision()
            except:
                pass

    def load_from_clipboard(self) -> bool:
        """Load image from clipboard."""
        try:
            # This is platform-specific
            # On Windows, use win32clipboard
            # On Linux, use xclip/xsel
            # On macOS, use pbpaste
            import platform
            system = platform.system()

            if system == "Windows":
                try:
                    import win32clipboard
                    win32clipboard.OpenClipboard()
                    if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
                        data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
                        import io

                        from PIL import Image
                        self._clipboard_image = Image.open(io.BytesIO(data))
                        win32clipboard.CloseClipboard()
                        return True
                    win32clipboard.CloseClipboard()
                except ImportError:
                    pass
            elif system == "Darwin":
                # macOS - use pbpaste
                pass
            elif system == "Linux":
                # Linux - use xclip
                pass
        except Exception:
            pass
        return False

    def load_from_file(self, path: str) -> bool:
        """Load image from file."""
        try:
            self._clipboard_image = Image.open(path)
            return True
        except Exception:
            return False

    def load_from_base64(self, b64_data: str) -> bool:
        """Load image from base64 string."""
        try:
            data = base64.b64decode(b64_data)
            self._clipboard_image = Image.open(io.BytesIO(data))
            return True
        except Exception:
            return False

    def get_image(self) -> Image.Image | None:
        return self._clipboard_image

    async def analyze(self, prompt: str = "Describe this image in detail.", image: Image.Image = None) -> str:
        if not self.provider:
            self.auto_configure()
        if not self.provider:
            return "No vision provider available. Set OPENAI_API_KEY, ANTHROPIC_TOKEN, or install transformers."

        image = image or self._clipboard_image
        if not image:
            return "No image loaded. Use load_from_clipboard(), load_from_file(), or load_from_base64()."

        return await self.provider.analyze(image, prompt)

    async def extract_text(self, image: Image.Image = None) -> str:
        if not self.provider:
            self.auto_configure()
        if not self.provider:
            return "No vision provider available."

        image = image or self._clipboard_image
        if not image:
            return "No image loaded."

        return await self.provider.extract_text(image)

    async def answer_question(self, question: str, image: Image.Image = None) -> str:
        if not self.provider:
            self.auto_configure()
        if not self.provider:
            return "No vision provider available."

        image = image or self._clipboard_image
        if not image:
            return "No image loaded."

        return await self.provider.answer_question(image, question)

    def get_image_info(self) -> dict:
        if not self._clipboard_image:
            return {"loaded": False}

        img = self._clipboard_image
        return {
            "loaded": True,
            "size": img.size,
            "mode": img.mode,
            "format": img.format,
        }


# =============================================================================
# Vision Tool for Agent
# =============================================================================

VISION_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "vision",
        "description": "Analyze images: describe, extract text, answer questions. Load from clipboard, file, or base64.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["analyze", "extract_text", "answer_question", "load_clipboard", "load_file", "load_base64", "info"],
                    "description": "Action to perform",
                },
                "prompt": {"type": "string", "description": "Prompt for analysis"},
                "question": {"type": "string", "description": "Question about image"},
                "file_path": {"type": "string", "description": "Image file path"},
                "base64": {"type": "string", "description": "Base64 encoded image"},
            },
            "required": ["action"],
        },
    },
}


async def vision_tool(action: str, **kwargs) -> str:
    """Vision tool handler."""
    import json

    manager = VisionManager()
    manager.auto_configure()

    try:
        if action == "load_clipboard":
            success = manager.load_from_clipboard()
            return json.dumps({"success": success, "info": manager.get_image_info()})

        elif action == "load_file":
            file_path = kwargs.get("file_path")
            if not file_path:
                return json.dumps({"error": "file_path required"})
            success = manager.load_from_file(file_path)
            return json.dumps({"success": success, "info": manager.get_image_info()})

        elif action == "load_base64":
            b64 = kwargs.get("base64")
            if not b64:
                return json.dumps({"error": "base64 required"})
            success = manager.load_from_base64(b64)
            return json.dumps({"success": success, "info": manager.get_image_info()})

        elif action == "info":
            return json.dumps(manager.get_image_info())

        # Actions requiring loaded image
        image = manager.get_image()
        if not image:
            return json.dumps({"error": "No image loaded. Use load_clipboard, load_file, or load_base64 first."})

        if action == "analyze":
            prompt = kwargs.get("prompt", "Describe this image in detail.")
            result = await manager.analyze(prompt)
            return json.dumps({"result": result})

        elif action == "extract_text":
            result = await manager.extract_text()
            return json.dumps({"text": result})

        elif action == "answer_question":
            question = kwargs.get("question")
            if not question:
                return json.dumps({"error": "question required"})
            result = await manager.answer_question(question)
            return json.dumps({"answer": result})

        else:
            return json.dumps({"error": f"Unknown action: {action}"})

    except Exception as e:
        return json.dumps({"error": str(e)})
