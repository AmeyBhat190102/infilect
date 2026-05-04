from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def build_username_map(self, usernames: list[str]) -> dict[str, int]:
        """
        Fetch PK ids for a batch of usernames in a single query.
        Returns {username: pk_id}.
        """
        result = await self.session.execute(
            select(User.username, User.id).where(User.username.in_(usernames))
        )
        return {row[0]: row[1] for row in result.fetchall()}
