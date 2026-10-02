from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.services.chat_service import ChatService
from app.services.llm.router import LLMRouter
from app.services.stt.service import TranscriptionService


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


def get_llm_router(request: Request) -> LLMRouter:
    return request.app.state.llm_router


def get_transcription_service(request: Request) -> TranscriptionService:
    return request.app.state.transcription_service


def get_request_id(request: Request) -> str:
    return request.state.request_id


def get_user_id(settings: Annotated[Settings, Depends(get_settings)]) -> str:
    # V1 is single-user; replace with the authenticated user once auth is added.
    return settings.local_user_id


def get_chat_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    router: Annotated[LLMRouter, Depends(get_llm_router)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatService:
    return ChatService(session, router, max_history_messages=settings.max_history_messages)


SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
RouterDep = Annotated[LLMRouter, Depends(get_llm_router)]
TranscriptionDep = Annotated[TranscriptionService, Depends(get_transcription_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
RequestIdDep = Annotated[str, Depends(get_request_id)]
UserIdDep = Annotated[str, Depends(get_user_id)]
