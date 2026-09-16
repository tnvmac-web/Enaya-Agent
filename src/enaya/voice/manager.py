#!/usr/bin/env python3
"""
Enaya Agent - Voice Module
Real-time voice conversations with STT/TTS providers.
"""

from __future__ import annotations

import asyncio
import os
import wave
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass

# =============================================================================
# Audio Data Classes
# =============================================================================


@dataclass
class AudioChunk:
    """Audio data chunk."""

    data: bytes
    sample_rate: int
    channels: int
    sample_width: int
    timestamp: float


@dataclass
class VoiceConfig:
    """Voice configuration."""

    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2  # 16-bit
    chunk_duration_ms: int = 100
    silence_threshold: float = 0.01
    silence_duration_ms: int = 500


# =============================================================================
# STT Providers (Abstract Base)
# =============================================================================


class STTProvider(ABC):
    """Speech-to-Text provider base class."""

    @abstractmethod
    async def transcribe(self, audio: bytes, sample_rate: int = 16000) -> str:
        """Transcribe audio to text."""
        pass

    @abstractmethod
    async def transcribe_stream(
        self, audio_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[str, None]:
        """Stream transcription."""
        pass


class LocalWhisperSTT(STTProvider):
    """Local faster-whisper STT."""

    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        try:
            from faster_whisper import WhisperModel

            self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        except ImportError:
            raise RuntimeError("faster-whisper not installed. Run: pip install faster-whisper")

    async def transcribe(self, audio: bytes, sample_rate: int = 16000) -> str:
        import io

        # Save to temporary WAV
        with io.BytesIO() as wav_io:
            with wave.open(wav_io, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio)
            wav_io.seek(0)

            segments, _ = self.model.transcribe(wav_io, language="en")
            return " ".join(seg.text for seg in segments)

    async def transcribe_stream(
        self, audio_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[str, None]:
        # Simplified - collect and transcribe in chunks
        buffer = bytearray()
        async for chunk in audio_stream:
            buffer.extend(chunk)
            if len(buffer) >= 16000 * 2:  # ~1 second at 16kHz
                text = await self.transcribe(bytes(buffer))
                if text.strip():
                    yield text
                buffer.clear()

        if buffer:
            text = await self.transcribe(bytes(buffer))
            if text.strip():
                yield text


class GroqSTT(STTProvider):
    """Groq Whisper STT."""

    def __init__(self, api_key: str = None, model: str = "whisper-large-v3-turbo"):
        from groq import Groq

        self.client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))
        self.model = model

    async def transcribe(self, audio: bytes, sample_rate: int = 16000) -> str:
        import io

        with io.BytesIO() as wav_io:
            with wave.open(wav_io, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio)
            wav_io.seek(0)

            transcription = self.client.audio.transcriptions.create(
                file=("audio.wav", wav_io.read()),
                model=self.model,
                language="en",
            )
            return transcription.text

    async def transcribe_stream(
        self, audio_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[str, None]:
        buffer = bytearray()
        async for chunk in audio_stream:
            buffer.extend(chunk)
            if len(buffer) >= 16000 * 2:
                text = await self.transcribe(bytes(buffer))
                if text.strip():
                    yield text
                buffer.clear()

        if buffer:
            text = await self.transcribe(bytes(buffer))
            if text.strip():
                yield text


# =============================================================================
# TTS Providers (Abstract Base)
# =============================================================================


class TTSProvider(ABC):
    """Text-to-Speech provider base class."""

    @abstractmethod
    async def synthesize(self, text: str, voice: str = "default") -> bytes:
        """Synthesize text to audio bytes."""
        pass

    @abstractmethod
    async def synthesize_stream(
        self, text: str, voice: str = "default"
    ) -> AsyncGenerator[bytes, None]:
        """Stream audio synthesis."""
        pass


class OpenAITTS(TTSProvider):
    """OpenAI TTS provider."""

    def __init__(self, api_key: str = None, model: str = "tts-1", voice: str = "alloy"):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.model = model
        self.default_voice = voice

    async def synthesize(self, text: str, voice: str = None) -> bytes:
        response = self.client.audio.speech.create(
            model=self.model,
            voice=voice or self.default_voice,
            input=text,
            response_format="mp3",
        )
        return response.content

    async def synthesize_stream(self, text: str, voice: str = None) -> AsyncGenerator[bytes, None]:
        response = self.client.audio.speech.create(
            model=self.model,
            voice=voice or self.default_voice,
            input=text,
            response_format="mp3",
        )
        # Stream in chunks
        for chunk in response.iter_bytes(chunk_size=1024):
            yield chunk


class ElevenLabsTTS(TTSProvider):
    """ElevenLabs TTS provider."""

    def __init__(
        self,
        api_key: str = None,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        model: str = "eleven_multilingual_v2",
    ):
        from elevenlabs import ElevenLabs

        self.client = ElevenLabs(api_key=api_key or os.environ.get("ELEVENLABS_API_KEY"))
        self.voice_id = voice_id
        self.model = model

    async def synthesize(self, text: str, voice: str = None) -> bytes:
        audio = self.client.generate(
            text=text,
            voice=voice or self.voice_id,
            model=self.model,
        )
        return b"".join(audio)

    async def synthesize_stream(self, text: str, voice: str = None) -> AsyncGenerator[bytes, None]:
        audio_stream = self.client.generate(
            text=text,
            voice=voice or self.voice_id,
            model=self.model,
            stream=True,
        )
        for chunk in audio_stream:
            yield chunk


# =============================================================================
# Voice Manager
# =============================================================================


class VoiceManager:
    """Manages voice conversations with STT/TTS."""

    def __init__(self, config: VoiceConfig = None):
        self.config = config or VoiceConfig()
        self.stt: STTProvider | None = None
        self.tts: TTSProvider | None = None
        self._audio_buffer = bytearray()

    def set_stt(self, provider: STTProvider) -> None:
        self.stt = provider

    def set_tts(self, provider: TTSProvider) -> None:
        self.tts = provider

    def auto_configure(self) -> None:
        """Auto-configure based on available API keys."""
        # STT
        if os.environ.get("GROQ_API_KEY"):
            self.stt = GroqSTT()
        elif os.environ.get("OPENAI_API_KEY"):
            try:
                # Use OpenAI Whisper
                pass
            except Exception:
                pass

        if not self.stt:
            try:
                self.stt = LocalWhisperSTT()
            except Exception:
                pass

        # TTS
        if os.environ.get("ELEVENLABS_API_KEY"):
            self.tts = ElevenLabsTTS()
        elif os.environ.get("OPENAI_API_KEY"):
            self.tts = OpenAITTS()

    async def voice_chat(self, text: str = None, audio: bytes = None) -> dict:
        """Process voice chat: STT -> Agent -> TTS."""
        result = {"text": "", "audio": None}

        # STT if audio provided
        if audio and self.stt:
            result["text"] = await self.stt.transcribe(audio)
        elif text:
            result["text"] = text
        else:
            return result

        # Process with agent (placeholder - integrate with agent)
        # response_text = await agent.run_conversation(result["text"])
        response_text = f"Echo: {result['text']}"  # Placeholder

        # TTS
        if self.tts:
            result["audio"] = await self.tts.synthesize(response_text)
            result["response_text"] = response_text

        return result


# =============================================================================
# Voice Gateway Integration
# =============================================================================


class VoiceGateway:
    """Voice integration for gateway platforms."""

    def __init__(self, runner, voice_manager: VoiceManager):
        self.runner = runner
        self.voice = voice_manager
        self._active_calls: dict[str, asyncio.Task] = {}

    async def handle_voice_message(
        self, platform: str, chat_id: str, user_id: str, audio_data: bytes
    ) -> None:
        """Handle incoming voice message."""
        if not self.voice.stt or not self.voice.tts:
            # Send error message
            return

        # STT
        text = await self.voice.stt.transcribe(audio_data)
        if not text.strip():
            return

        # Create message event
        from enaya.gateway.runner import MessageEvent

        MessageEvent(
            platform=platform,
            chat_type="voice",
            chat_id=chat_id,
            user_id=user_id,
            text=f"[VOICE] {text}",
        )

        # Process through gateway (will get text response)
        # Then TTS the response
        # This is a simplified integration
        pass

    async def send_voice_reply(self, platform: str, chat_id: str, text: str) -> None:
        """Send voice reply."""
        if not self.voice.tts:
            return

        audio = await self.voice.tts.synthesize(text)

        # Platform-specific voice sending
        adapter = self.runner._adapters.get(platform)
        if adapter and hasattr(adapter, "send_voice"):
            await adapter.send_voice(chat_id, audio)


# =============================================================================
# Wake Word Detection
# =============================================================================


class WakeWordDetector:
    """Wake word detection for 'Hey Enaya'."""

    def __init__(self, wake_word: str = "hey enaya", sensitivity: float = 0.5):
        self.wake_word = wake_word.lower()
        self.sensitivity = sensitivity
        self._listening = False

    async def start_listening(self, callback: callable) -> None:
        """Start wake word detection."""
        # This would use a library like pvporcupine or custom implementation
        # Simplified placeholder
        self._listening = True

    async def stop_listening(self) -> None:
        self._listening = False
