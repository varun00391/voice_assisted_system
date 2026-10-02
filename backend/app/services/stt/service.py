import asyncio
import logging
import time
from pathlib import PurePath

from fastapi import UploadFile

from app.config.settings import Settings
from app.core.errors import (
    AppError,
    AudioTooLargeError,
    AudioValidationError,
    EmptyTranscriptError,
    TranscriptionError,
    UnsupportedAudioFormatError,
)
from app.providers.stt.base import STTProvider, TranscriptionResult

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/aac",
    "audio/flac",
}
ALLOWED_EXTENSIONS = {".webm", ".ogg", ".oga", ".wav", ".mp3", ".mp4", ".m4a", ".aac", ".flac"}
GENERIC_CONTENT_TYPES = {"", "application/octet-stream"}


class TranscriptionService:
    """Validates uploads, bounds concurrency/time and delegates to the STT provider."""

    def __init__(self, provider: STTProvider, settings: Settings):
        self._provider = provider
        self._settings = settings
        self._semaphore = asyncio.Semaphore(max(1, settings.max_concurrent_transcriptions))

    async def transcribe_upload(self, upload: UploadFile) -> TranscriptionResult:
        audio = await self._read_validated(upload)
        started = time.perf_counter()
        logger.info("stt started", extra={"audio_bytes": len(audio)})
        try:
            async with asyncio.timeout(self._settings.stt_timeout_seconds):
                async with self._semaphore:
                    result = await self._provider.transcribe(
                        audio, max_duration_seconds=self._settings.max_audio_duration_seconds
                    )
        except TimeoutError as exc:
            raise TranscriptionError("Transcription took too long. Please try a shorter recording.") from exc
        except AppError:
            raise
        except Exception as exc:
            logger.exception("stt failed")
            raise TranscriptionError() from exc

        logger.info(
            "stt completed",
            extra={
                "duration_ms": round((time.perf_counter() - started) * 1000),
                "audio_seconds": result.duration_seconds,
                "language": result.language,
            },
        )
        if not result.text.strip():
            raise EmptyTranscriptError()
        return result

    async def _read_validated(self, upload: UploadFile) -> bytes:
        content_type = (upload.content_type or "").split(";")[0].strip().lower()
        extension = PurePath(upload.filename or "").suffix.lower()
        if content_type not in ALLOWED_CONTENT_TYPES and not (
            content_type in GENERIC_CONTENT_TYPES and extension in ALLOWED_EXTENSIONS
        ):
            raise UnsupportedAudioFormatError(
                "This audio format is not supported. Use WebM, Ogg, WAV, MP3, M4A or FLAC."
            )

        max_bytes = self._settings.max_audio_size_bytes
        audio = await upload.read(max_bytes + 1)
        if len(audio) > max_bytes:
            raise AudioTooLargeError(
                f"The recording is too large. Maximum size is {self._settings.max_audio_size_mb:g} MB."
            )
        if not audio:
            raise AudioValidationError("The audio file is empty. Please try recording again.")
        return audio
