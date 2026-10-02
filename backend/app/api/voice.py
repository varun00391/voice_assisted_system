from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import ValidationError

from app.api.deps import ChatServiceDep, RequestIdDep, TranscriptionDep, UserIdDep
from app.core.errors import AudioValidationError
from app.schemas.chat import ChatRequest
from app.schemas.voice import TranscriptionResponse, VoiceChatResponse
from app.services.modes.config import DEFAULT_MODE

router = APIRouter(prefix="/api/v1", tags=["voice"])


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(transcription: TranscriptionDep, audio: Annotated[UploadFile, File()]) -> TranscriptionResponse:
    result = await transcription.transcribe_upload(audio)
    return TranscriptionResponse(text=result.text, language=result.language, duration_seconds=result.duration_seconds)


@router.post("/voice/chat", response_model=VoiceChatResponse)
async def voice_chat(
    transcription: TranscriptionDep,
    chat_service: ChatServiceDep,
    user_id: UserIdDep,
    request_id: RequestIdDep,
    audio: Annotated[UploadFile, File()],
    mode: Annotated[str, Form()] = DEFAULT_MODE,
    provider: Annotated[str | None, Form()] = None,
    conversation_id: Annotated[str | None, Form()] = None,
    custom_instructions: Annotated[str | None, Form()] = None,
) -> VoiceChatResponse:
    result = await transcription.transcribe_upload(audio)
    try:
        payload = ChatRequest(
            message=result.text,
            mode=mode,
            provider=provider,
            conversation_id=conversation_id or None,
            custom_instructions=custom_instructions,
        )
    except ValidationError as exc:
        raise AudioValidationError(exc.errors()[0]["msg"]) from exc

    outcome = await chat_service.answer(
        user_id=user_id,
        request_id=request_id,
        question=payload.message,
        mode_key=payload.mode,
        conversation_id=payload.conversation_id,
        custom_instructions=payload.custom_instructions,
        preferred_provider=payload.provider,
    )
    return VoiceChatResponse(transcript=payload.message, **vars(outcome))
