from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError
from app.models.entities import Conversation, LLMRequestLog, Message
from app.services.llm.router import ProviderAttempt

TITLE_MAX_LENGTH = 60


def make_title(question: str) -> str:
    title = " ".join(question.split())
    return title if len(title) <= TITLE_MAX_LENGTH else title[: TITLE_MAX_LENGTH - 1].rstrip() + "…"


class ConversationStore:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, user_id: str, *, title: str, mode: str, created_at: datetime) -> Conversation:
        conversation = Conversation(
            user_id=user_id, title=title, mode=mode, created_at=created_at, updated_at=created_at
        )
        self._session.add(conversation)
        await self._session.flush()
        return conversation

    async def get(self, user_id: str, conversation_id: str, *, with_messages: bool = False) -> Conversation:
        query = select(Conversation).where(
            Conversation.conversation_id == conversation_id, Conversation.user_id == user_id
        )
        if with_messages:
            query = query.options(selectinload(Conversation.messages))
        conversation = await self._session.scalar(query)
        if conversation is None:
            raise NotFoundError("Conversation not found.")
        return conversation

    async def list_for_user(self, user_id: str) -> list[Conversation]:
        result = await self._session.scalars(
            select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc())
        )
        return list(result)

    async def delete(self, user_id: str, conversation_id: str) -> None:
        conversation = await self.get(user_id, conversation_id)
        await self._session.delete(conversation)

    async def recent_messages(self, conversation_id: str, limit: int) -> list[Message]:
        if limit <= 0:
            return []
        result = await self._session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return list(reversed(list(result)))

    async def add_message(
        self,
        conversation: Conversation,
        *,
        role: str,
        content: str,
        created_at: datetime,
        mode: str | None = None,
        provider: str | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation.conversation_id,
            role=role,
            content=content,
            mode=mode,
            provider=provider,
            created_at=created_at,
        )
        self._session.add(message)
        conversation.updated_at = created_at
        await self._session.flush()
        return message

    def log_attempts(self, request_id: str, conversation_id: str | None, attempts: list[ProviderAttempt]) -> None:
        self._session.add_all(
            LLMRequestLog(
                request_id=request_id,
                conversation_id=conversation_id,
                provider=attempt.provider,
                model=attempt.model,
                status=attempt.status,
                latency_ms=attempt.latency_ms,
                error_type=attempt.error_type,
            )
            for attempt in attempts
        )
