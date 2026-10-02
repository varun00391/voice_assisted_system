from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import User, utc_now


class UserContextStore:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def ensure_user(self, user_id: str) -> User:
        user = await self._session.get(User, user_id)
        if user is None:
            user = User(user_id=user_id, context={})
            self._session.add(user)
            await self._session.flush()
        return user

    async def get(self, user_id: str) -> dict[str, Any]:
        user = await self._session.get(User, user_id)
        return dict(user.context or {}) if user else {}

    async def replace(self, user_id: str, context: dict[str, Any]) -> dict[str, Any]:
        user = await self.ensure_user(user_id)
        user.context = _compact(context)
        user.updated_at = utc_now()
        return dict(user.context)

    async def merge(self, user_id: str, partial: dict[str, Any]) -> dict[str, Any]:
        user = await self.ensure_user(user_id)
        user.context = _compact({**(user.context or {}), **partial})
        user.updated_at = utc_now()
        return dict(user.context)

    async def clear(self, user_id: str) -> None:
        user = await self._session.get(User, user_id)
        if user is not None:
            user.context = {}
            user.updated_at = utc_now()


def _compact(context: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in context.items() if value not in (None, "", [])}
