from typing import Any


class AppError(Exception):
    """Error whose message is safe to show to end users."""

    status_code = 500
    code = "internal_error"
    default_message = "Something went wrong. Please try again."

    def __init__(self, message: str | None = None, *, attempts: list[Any] | None = None):
        self.message = message or self.default_message
        self.attempts = attempts or []
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    default_message = "The requested resource was not found."


class AudioValidationError(AppError):
    status_code = 400
    code = "invalid_audio"
    default_message = "The audio file is invalid. Please try recording again."


class UnsupportedAudioFormatError(AppError):
    status_code = 415
    code = "unsupported_audio_format"
    default_message = "This audio format is not supported."


class AudioTooLargeError(AppError):
    status_code = 413
    code = "audio_too_large"
    default_message = "The recording is too large."


class AudioTooLongError(AppError):
    status_code = 400
    code = "audio_too_long"
    default_message = "The recording is too long."


class TranscriptionError(AppError):
    status_code = 500
    code = "transcription_failed"
    default_message = "Unable to transcribe the audio. Please try again."


class EmptyTranscriptError(AppError):
    status_code = 422
    code = "empty_transcript"
    default_message = "No speech was detected. Please try again."


class AllProvidersUnavailableError(AppError):
    status_code = 503
    code = "llm_unavailable"
    default_message = "The AI providers are temporarily unavailable. Please try again shortly."


class NoProvidersConfiguredError(AppError):
    status_code = 503
    code = "llm_not_configured"
    default_message = "No AI providers are configured. Add an API key to the .env file."


class ProviderNotConfiguredError(AppError):
    status_code = 400
    code = "provider_not_configured"
    default_message = "The selected AI provider is not configured. Choose another provider."


class LLMRequestRejectedError(AppError):
    status_code = 502
    code = "llm_request_rejected"
    default_message = "The AI provider rejected the request. Please check the server configuration."


class RateLimitExceededError(AppError):
    status_code = 429
    code = "rate_limited"
    default_message = "Too many requests. Please wait a moment and try again."
