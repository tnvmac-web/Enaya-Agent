#!/usr/bin/env python3
"""
Enaya Agent - Image Generation Module
Image generation via FAL.ai, OpenAI, and other providers.
"""

from __future__ import annotations

import asyncio
import base64
import io
import os
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import httpx
from PIL import Image

# =============================================================================
# Image Generation Models
# =============================================================================


class ImageModel(Enum):
    """Supported image generation models."""

    FLUX_PRO = "fal-ai/flux-pro"
    FLUX_DEV = "fal-ai/flux-dev"
    FLUX_SCHNELL = "fal-ai/flux-schnell"
    FLUX_REALISM = "fal-ai/flux-realism"
    IDEOGRAM_V2 = "fal-ai/ideogram/v2"
    IDEOGRAM_V2_TURBO = "fal-ai/ideogram/v2/turbo"
    RECRAFT_V3 = "fal-ai/recraft-v3"
    RECRAFT_V3_TURBO = "fal-ai/recraft-v3-turbo"
    KREA_V2 = "fal-ai/krea-v2"
    NANO_BANANA = "fal-ai/nano-banana"
    NANO_BANANA_PRO = "fal-ai/nano-banana-pro"
    GPT_IMAGE_1 = "fal-ai/gpt-image-1"
    STABLE_DIFFUSION_XL = "fal-ai/stable-diffusion-xl"
    MIDJOURNEY_V6 = "fal-ai/midjourney-v6"
    DALL_E_3 = "openai/dall-e-3"
    GPT_IMAGE = "openai/gpt-image-1"


@dataclass
class ImageGenerationConfig:
    """Configuration for image generation."""

    model: ImageModel = ImageModel.FLUX_DEV
    width: int = 1024
    height: int = 1024
    num_images: int = 1
    steps: int = 28
    guidance_scale: float = 3.5
    seed: int | None = None
    prompt_strength: float = 0.8
    negative_prompt: str = ""
    format: str = "png"  # png, jpeg, webp
    quality: int = 90


# =============================================================================
# Provider Interface
# =============================================================================


class ImageGenProvider(ABC):
    """Abstract image generation provider."""

    @abstractmethod
    async def generate(self, prompt: str, config: ImageGenerationConfig) -> list[bytes]:
        """Generate images from prompt."""
        pass

    @abstractmethod
    async def generate_stream(
        self, prompt: str, config: ImageGenerationConfig
    ) -> AsyncGenerator[bytes, None]:
        """Stream image generation."""
        pass

    @abstractmethod
    def get_supported_models(self) -> list[ImageModel]:
        """Get list of supported models."""
        pass


# =============================================================================
# FAL.ai Provider
# =============================================================================


class FalAIProvider(ImageGenProvider):
    """FAL.ai image generation provider."""

    MODEL_MAP = {
        ImageModel.FLUX_PRO: "fal-ai/flux-pro",
        ImageModel.FLUX_DEV: "fal-ai/flux-dev",
        ImageModel.FLUX_SCHNELL: "fal-ai/flux-schnell",
        ImageModel.FLUX_REALISM: "fal-ai/flux-realism",
        ImageModel.IDEOGRAM_V2: "fal-ai/ideogram/v2",
        ImageModel.IDEOGRAM_V2_TURBO: "fal-ai/ideogram/v2/turbo",
        ImageModel.RECRAFT_V3: "fal-ai/recraft-v3",
        ImageModel.RECRAFT_V3_TURBO: "fal-ai/recraft-v3-turbo",
        ImageModel.KREA_V2: "fal-ai/krea-v2",
        ImageModel.NANO_BANANA: "fal-ai/nano-banana",
        ImageModel.NANO_BANANA_PRO: "fal-ai/nano-banana-pro",
        ImageModel.GPT_IMAGE_1: "fal-ai/gpt-image-1",
        ImageModel.STABLE_DIFFUSION_XL: "fal-ai/stable-diffusion-xl",
        ImageModel.MIDJOURNEY_V6: "fal-ai/midjourney-v6",
    }

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("FAL_KEY") or os.environ.get("FAL_API_KEY")
        if not self.api_key:
            raise RuntimeError("FAL_KEY or FAL_API_KEY environment variable required")
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Key {self.api_key}"},
            timeout=300.0,
        )

    async def generate(self, prompt: str, config: ImageGenerationConfig) -> list[bytes]:
        model_endpoint = self.MODEL_MAP.get(config.model)
        if not model_endpoint:
            raise ValueError(f"Model {config.model} not supported by FAL.ai")

        payload = {
            "prompt": prompt,
            "image_size": self._get_size_string(config.width, config.height),
            "num_images": config.num_images,
            "num_inference_steps": config.steps,
            "guidance_scale": config.guidance_scale,
            "seed": config.seed,
            "negative_prompt": config.negative_prompt,
            "format": config.format,
        }

        # Add model-specific parameters
        if "flux" in model_endpoint.lower():
            payload["enable_safety_checker"] = False

        async with httpx.AsyncClient(
            headers={"Authorization": f"Key {self.api_key}"},
            timeout=300.0,
        ) as client:
            # Submit generation
            resp = await client.post(
                f"https://queue.fal.run/{model_endpoint}",
                json=payload,
                timeout=60.0,
            )
            resp.raise_for_status()
            result = resp.json()

            # Handle queue response
            if "request_id" in result:
                request_id = result["request_id"]
                status_url = f"https://queue.fal.run/{model_endpoint}/requests/{request_id}/status"

                # Poll for completion
                async with httpx.AsyncClient(timeout=300.0) as client:
                    while True:
                        status_resp = await client.get(status_url)
                        status_resp.raise_for_status()
                        status = status_resp.json()

                        if status["status"] == "COMPLETED":
                            break
                        elif status["status"] in ("FAILED", "CANCELLED"):
                            raise RuntimeError(
                                f"Generation failed: {status.get('error', 'Unknown error')}"
                            )

                        await asyncio.sleep(2)

                # Get result
                result_url = f"https://queue.fal.run/{model_endpoint}/requests/{request_id}"
                async with httpx.AsyncClient(timeout=60.0) as client:
                    result_resp = await client.get(result_url)
                    result_resp.raise_for_status()
                    result = result_resp.json()

            # Download images
            images = []
            for img_data in result.get("images", []):
                img_url = img_data["url"]
                async with httpx.AsyncClient(timeout=60.0) as client:
                    img_resp = await client.get(img_url)
                    img_resp.raise_for_status()
                    images.append(img_resp.content)

            return images

    async def generate_stream(
        self, prompt: str, config: ImageGenerationConfig
    ) -> AsyncGenerator[bytes, None]:
        # For now, just yield after full generation
        images = await self.generate(prompt, config)
        for img in images:
            yield img

    def get_supported_models(self) -> list[ImageModel]:
        return list(self.MODEL_MAP.keys())

    def _get_size_string(self, width: int, height: int) -> str:
        """Convert dimensions to FAL.ai size string."""
        if width == height:
            if width <= 512:
                return "square_hd"
            elif width <= 1024:
                return "square"
            else:
                return "square_hd"
        elif width > height:
            if width <= 1024:
                return "landscape_4_3"
            else:
                return "landscape_16_9"
        else:
            if height <= 1024:
                return "portrait_4_3"
            else:
                return "portrait_16_9"


# =============================================================================
# OpenAI Provider
# =============================================================================


class OpenAIProvider(ImageGenProvider):
    """OpenAI DALL-E / GPT-Image provider."""

    def __init__(self, api_key: str = None):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    async def generate(self, prompt: str, config: ImageGenerationConfig) -> list[bytes]:

        # Map models
        model_map = {
            ImageModel.DALL_E_3: "dall-e-3",
            ImageModel.GPT_IMAGE: "gpt-image-1",
        }

        model = model_map.get(config.model, "dall-e-3")

        response = self.client.images.generate(
            model=model,
            prompt=prompt,
            n=config.num_images,
            size=f"{config.width}x{config.height}",
            quality="hd" if config.quality >= 90 else "standard",
            style="vivid",
            response_format="b64_json",
        )

        images = []
        for img_data in response.data:
            images.append(base64.b64decode(img_data.b64_json))

        return images

    async def generate_stream(
        self, prompt: str, config: ImageGenerationConfig
    ) -> AsyncGenerator[bytes, None]:
        images = await self.generate(prompt, config)
        for img in images:
            yield img

    def get_supported_models(self) -> list[ImageModel]:
        return [ImageModel.DALL_E_3, ImageModel.GPT_IMAGE]


# =============================================================================
# Image Generation Manager
# =============================================================================


class ImageGenManager:
    """Manages image generation across providers."""

    def __init__(self):
        self.providers: dict[str, ImageGenProvider] = {}
        self.default_provider = "fal"

    def add_provider(self, name: str, provider: ImageGenProvider) -> None:
        self.providers[name] = provider

    def set_default(self, name: str) -> None:
        if name in self.providers:
            self.default_provider = name

    def get_provider(self, name: str = None) -> ImageGenProvider | None:
        name = name or self.default_provider
        return self.providers.get(name)

    def auto_configure(self) -> None:
        """Auto-configure based on available API keys."""
        if os.environ.get("FAL_KEY") or os.environ.get("FAL_API_KEY"):
            try:
                self.providers["fal"] = FalAIProvider()
                self.default_provider = "fal"
            except Exception:
                pass

        if os.environ.get("OPENAI_API_KEY"):
            try:
                self.providers["openai"] = OpenAIProvider()
                if self.default_provider not in self.providers:
                    self.default_provider = "openai"
            except Exception:
                pass

    def list_models(self) -> dict[str, list[str]]:
        """List available models per provider."""
        result = {}
        for name, provider in self.providers.items():
            result[name] = [m.value for m in provider.get_supported_models()]
        return result

    async def generate(
        self,
        prompt: str,
        provider: str = None,
        model: ImageModel = None,
        **kwargs,
    ) -> list[bytes]:
        """Generate images."""
        prov = self.get_provider(provider)
        if not prov:
            raise RuntimeError(f"No provider available. Available: {list(self.providers.keys())}")

        config = ImageGenerationConfig(model=model or ImageModel.FLUX_DEV, **kwargs)
        return await prov.generate(prompt, config)

    async def generate_and_save(
        self,
        prompt: str,
        output_dir: str = "./generated",
        provider: str = None,
        model: ImageModel = None,
        **kwargs,
    ) -> list[str]:
        """Generate and save images to disk."""
        images = await self.generate(prompt, provider, model, **kwargs)

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        saved_paths = []

        for i, img_bytes in enumerate(images):
            img = Image.open(io.BytesIO(img_bytes))
            ext = "png"
            filename = f"generated_{int(time.time())}_{i}.{ext}"
            path = Path(output_dir) / filename
            img.save(path)
            saved_paths.append(str(path))

        return saved_paths


# =============================================================================
# Image Generation Tool for Agent
# =============================================================================

IMAGE_GEN_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "image_gen",
        "description": (
            "Generate images using AI models (FLUX, DALL-E, Ideogram, "
            "etc.) via FAL.ai or OpenAI."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Image generation prompt"
                },
                "model": {
                    "type": "string",
                    "enum": [m.value for m in ImageModel],
                    "description": "Model to use",
                },
                "provider": {
                    "type": "string",
                    "description": "Provider (fal, openai)"
                },
                "width": {"type": "integer", "default": 1024},
                "height": {"type": "integer", "default": 1024},
                "num_images": {"type": "integer", "default": 1},
                "steps": {"type": "integer", "default": 28},
                "guidance_scale": {"type": "number", "default": 3.5},
                "seed": {"type": "integer", "description": "Random seed"},
                "negative_prompt": {"type": "string", "default": ""},
                "save": {"type": "boolean", "default": False},
                "output_dir": {"type": "string", "default": "./generated"},
            },
            "required": ["prompt"],
        },
    },
}


async def image_gen_tool(prompt: str, **kwargs) -> str:
    """Image generation tool handler."""
    import json

    manager = ImageGenManager()
    manager.auto_configure()

    if not manager.providers:
        return json.dumps(
            {"error": "No image generation provider configured. Set FAL_KEY or OPENAI_API_KEY."}
        )

    try:
        model_str = kwargs.get("model")
        model = ImageModel(model_str) if model_str else None

        if kwargs.get("save"):
            paths = await manager.generate_and_save(
                prompt=prompt,
                provider=kwargs.get("provider"),
                model=model,
                output_dir=kwargs.get("output_dir", "./generated"),
                width=kwargs.get("width", 1024),
                height=kwargs.get("height", 1024),
                num_images=kwargs.get("num_images", 1),
                steps=kwargs.get("steps", 28),
                guidance_scale=kwargs.get("guidance_scale", 3.5),
                seed=kwargs.get("seed"),
                negative_prompt=kwargs.get("negative_prompt", ""),
            )
            return json.dumps(
                {
                    "success": True,
                    "paths": paths,
                    "count": len(paths),
                }
            )
        else:
            images = await manager.generate(
                prompt=prompt,
                provider=kwargs.get("provider"),
                model=model,
                width=kwargs.get("width", 1024),
                height=kwargs.get("height", 1024),
                num_images=kwargs.get("num_images", 1),
                steps=kwargs.get("steps", 28),
                guidance_scale=kwargs.get("guidance_scale", 3.5),
                seed=kwargs.get("seed"),
                negative_prompt=kwargs.get("negative_prompt", ""),
            )

            # Return as base64
            b64_images = [base64.b64encode(img).decode() for img in images]
            return json.dumps(
                {
                    "success": True,
                    "images": b64_images,
                    "count": len(b64_images),
                    "format": "base64_png",
                }
            )

    except Exception as e:
        return json.dumps({"error": str(e)})
