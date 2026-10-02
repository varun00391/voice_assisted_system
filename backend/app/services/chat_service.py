from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.entities import utc_now
from app.services.context.selector import select_relevant_context
from app.services.context.store import UserContextStore
from app.services.llm.router import LLMRouter, RouterResult
from app.services.memory.conversation_store import ConversationStore, make_title
from app.services.modes.config import get_mode
from app.services.prompt_builder import build_messages


@dataclass(frozen=True)
class ChatOutcome:
    conversation_id: str
    message_id: str
    answer: str
    mode: str
    provider: str
    fallback_used: bool
    truncated: bool


class ChatService:
    """Request processor: mode + history + relevant user context -> prompt -> LLM router -> persistence."""

    def __init__(self, session: AsyncSession, router: LLMRouter, *, max_history_messages: int):
        self._session = session
        self._router = router
        self._max_history = max_history_messages
        self._conversations = ConversationStore(session)
        self._contexts = UserContextStore(session)

    async def answer(
        self,
        *,
        user_id: str,
        request_id: str,
        question: str,
        mode_key: str,
        conversation_id: str | None,
        custom_instructions: str | None,
        preferred_provider: str | None = None,
    ) -> ChatOutcome:
        mode = get_mode(mode_key)
        received_at = utc_now()

        if conversation_id:
            conversation = await self._conversations.get(user_id, conversation_id)
            history = await self._conversations.recent_messages(conversation_id, self._max_history)
        else:
            conversation = None
            history = []

        user_context = select_relevant_context(question, mode.key, await self._contexts.get(user_id))
        messages = build_messages(
            question=question,
            mode=mode,
            history=history,
            user_context=user_context,
            custom_instructions=custom_instructions,
        )

        try:
            result: RouterResult = await self._router.generate(messages, preferred_provider=preferred_provider)
        except AppError as exc:
            if exc.attempts:
                self._conversations.log_attempts(request_id, conversation_id, exc.attempts)
                await self._session.commit()
            raise

        await self._contexts.ensure_user(user_id)
        if conversation is None:
            conversation = await self._conversations.create(
                user_id, title=make_title(question), mode=mode.key, created_at=received_at
            )
        conversation.mode = mode.key

        await self._conversations.add_message(
            conversation, role="user", content=question, mode=mode.key, created_at=received_at
        )
        assistant_message = await self._conversations.add_message(
            conversation,
            role="assistant",
            content=result.content,
            mode=mode.key,
            provider=result.provider,
            created_at=utc_now(),
        )
        self._conversations.log_attempts(request_id, conversation.conversation_id, result.attempts)
        await self._session.commit()

        return ChatOutcome(
            conversation_id=conversation.conversation_id,
            message_id=assistant_message.message_id,
            answer=result.content,
            mode=mode.key,
            provider=result.provider,
            fallback_used=result.fallback_used,
            truncated=result.truncated,
        )
