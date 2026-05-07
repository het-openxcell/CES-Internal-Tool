from app.db.pool import DatabasePool
from app.models.user import User


class UserRepository:
    def __init__(self, database_pool: DatabasePool) -> None:
        self.database_pool = database_pool

    async def find_by_username(self, username: str) -> User | None:
        pool = await self.database_pool.get()
        row = await pool.fetchrow(
            """
            SELECT id::text, username, password_hash, created_at, updated_at
            FROM users
            WHERE username = $1
            """,
            username,
        )
        if row is None:
            return None
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
