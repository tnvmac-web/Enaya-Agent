#!/usr/bin/env python3
"""
Enaya Agent - Voice Tool
Text-to-speech and speech-to-text.
"""

from __future__ import annotations

import json
import os
import base64
import io
from typing import Any

from enaya.tools.registry import registry
from enaya.voice.manager import VoiceManager


# =============================================================================
# Voice Tool
# =============================================================================

VOICE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "voice",
        "description": "Text-to-speech and speech-to-text operations. Supports multiple providers.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["tts", "stt", "list_voices"],
                    "description": "Action to perform"
                },
                "text": {"type": "string", "description": "Text to convert to speech (for tts)"},
                "audio_base64": {"type": "string", "description": "Base64 encoded audio data (for stt)"},
                "voice": {"type": "string", "description": "Voice to use (for tts)"},
                "provider": {"type": "string", "description": "Provider to use (openai, elevenlabs, local)"},
            },
            "required": ["action"],
        },
    },
}


def check_voice_requirements() -> bool:
    return True


_voice_manager = None


def _get_voice_manager():
    global _voice_manager
    if _voice_manager is None:
        _voice_manager = VoiceManager()
    return _voice_manager


def voice_tool(action: str, text: str = None, audio_base64: str = None, voice: str = None, provider: str = None) -> str:
    """Voice tool handler."""
    manager = _get_voice_manager()
    
    try:
        if action == "tts":
            if not text:
                return json.dumps({"error": "text required for tts"})
            
            vm = _get_voice_manager()
            vm.auto_configure()
            
            # Run async in sync context
            import asyncio
            audio_bytes = asyncio.run(vm.voice.synthesize(text, voice or "alloy"))
            
            b64_audio = base64.b64encode(audio_bytes).decode()
            return json.dumps({
                "success": True,
                "audio_base64": b64_audio,
                "format": "mp3",
            })
        
        elif action == "stt":
            if not audio_base64:
                return json.dumps({"error": "audio_base64 required for stt"})
            
            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_base64)
            
            vm = _get_voice_manager()
            vm.auto_configure()
            
            import asyncio
            text = asyncio.run(vm.voice.transcribe(audio_bytes))
            
            return json.dumps({
                "success": True,
                "text": text,
            })
        
        elif action == "list_voices":
            vm = _get_voice_manager()
            return json.dumps({
                "voices": [
                    {"id": "alloy", "name": "Alloy", "provider": "openai"},
                    {"id": "echo", "name": "Echo", "provider": "openai"},
                    {"id": "fable", "name": "Fable", "provider": "openai"},
                    {"id": "onyx", "name": "Onyx", "provider": "openai"},
                    {"id": "nova", "name": "Nova", "provider": "openai"},
                    {"id": "shimmer", "name": "Shimmer", "provider": "openai"},
                ]
            })
        
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    
    except Exception as e:
        return json.dumps({"error": str(e)})


def check_voice_requirements() -> bool:
    return True


registry.register(
    name="voice",
    toolset="voice",
    schema=VOICE_SCHEMA,
    handler=voice_tool,
    check_fn=check_voice_requirements,
)