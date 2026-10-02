from fastapi import APIRouter, Response, status

from app.api.deps import SessionDep, UserIdDep
from app.schemas.user_context import UserContext
from app.services.context.store import UserContextStore

router = APIRouter(prefix="/api/v1/user/context", tags=["user-context"])


@router.get("", response_model=UserContext)
async def get_user_context(session: SessionDep, user_id: UserIdDep) -> UserContext:
    return UserContext(**await UserContextStore(session).get(user_id))


@router.post("", response_model=UserContext)
async def replace_user_context(payload: UserContext, session: SessionDep, user_id: UserIdDep) -> UserContext:
    stored = await UserContextStore(session).replace(user_id, payload.model_dump())
    await session.commit()
    return UserContext(**stored)


@router.patch("", response_model=UserContext)
async def update_user_context(payload: UserContext, session: SessionDep, user_id: UserIdDep) -> UserContext:
    stored = await UserContextStore(session).merge(user_id, payload.model_dump(exclude_unset=True))
    await session.commit()
    return UserContext(**stored)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_context(session: SessionDep, user_id: UserIdDep) -> Response:
    await UserContextStore(session).clear(user_id)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
