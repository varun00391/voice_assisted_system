from fastapi import APIRouter

from app.api.deps import ChatServiceDep, RequestIdDep, UserIdDep
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest, chat_service: ChatServiceDep, user_id: UserIdDep, request_id: RequestIdDep
) -> ChatResponse:
    outcome = await chat_service.answer(
        user_id=user_id,
        request_id=request_id,
        question=payload.message,
        mode_key=payload.mode,
        conversation_id=payload.conversation_id,
        custom_instructions=payload.custom_instructions,
        preferred_provider=payload.provider,
    )
    return ChatResponse(**vars(outcome))
