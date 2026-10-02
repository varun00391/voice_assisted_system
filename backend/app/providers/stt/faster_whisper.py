import asyncio
import io
import logging
import threading
import time

from app.core.errors import AudioTooLongError, AudioValidationError, EmptyTranscriptError
from app.providers.stt.base import STTProvider, TranscriptionResult

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000


class FasterWhisperProvider(STTProvider):
    def __init__(self, *, model_size: str, device: str, compute_type: str, language: str | None = None):
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._language = language
        self._model = None
        self._lock = threading.Lock()

    def warm_up(self) -> None:
        self._load_model()

    def _load_model(self):
        with self._lock:
            if self._model is None:
                from faster_whisper import WhisperModel

                started = time.perf_counter()
                logger.info("loading whisper model", extra={"model": self._model_size, "device": self._device})
                self._model = WhisperModel(self._model_size, device=self._device, compute_type=self._compute_type)
                logger.info(
                    "whisper model loaded",
                    extra={"model": self._model_size, "duration_ms": round((time.perf_counter() - started) * 1000)},
                )
        return self._model

    async def transcribe(self, audio: bytes, *, max_duration_seconds: float) -> TranscriptionResult:
        return await asyncio.to_thread(self._transcribe_sync, audio, max_duration_seconds)

    def _transcribe_sync(self, audio: bytes, max_duration_seconds: float) -> TranscriptionResult:
        import av
        from faster_whisper import decode_audio

        try:
            samples = decode_audio(io.BytesIO(audio), sampling_rate=SAMPLE_RATE)
        except av.error.FFmpegError as exc:
            raise AudioValidationError("The audio could not be decoded. Please try recording again.") from exc

        duration = len(samples) / SAMPLE_RATE
        if duration == 0:
            raise EmptyTranscriptError()
        if duration > max_duration_seconds:
            raise AudioTooLongError(f"The recording is too long. Maximum duration is {int(max_duration_seconds)} seconds.")

        segments, info = self._load_model().transcribe(
            samples, language=self._language, vad_filter=True, beam_size=5
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return TranscriptionResult(text=text, language=info.language, duration_seconds=round(duration, 2))
