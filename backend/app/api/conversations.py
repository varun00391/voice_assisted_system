from fastapi import APIRouter, Response, status

from app.api.deps import SessionDep, UserIdDep
from app.schemas.conversation import ConversationDetail, ConversationSummary
from app.services.memory.conversation_store import ConversationStore

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(session: SessionDep, user_id: UserIdDep):
    return await ConversationStore(session).list_for_user(user_id)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str, session: SessionDep, user_id: UserIdDep):
    return await ConversationStore(session).get(user_id, conversation_id, with_messages=True)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: str, session: SessionDep, user_id: UserIdDep) -> Response:
    await ConversationStore(session).delete(user_id, conversation_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
