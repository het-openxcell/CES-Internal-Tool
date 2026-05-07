import asyncio

import asyncpg


class DatabasePool:
    def __init__(self, postgres_dsn: str) -> None:
        self.postgres_dsn = postgres_dsn
        self.pool: asyncpg.Pool | None = None
        self.lock = asyncio.Lock()

    async def get(self) -> asyncpg.Pool:
        if self.pool is None:
            async with self.lock:
                if self.pool is None:
                    self.pool = await asyncpg.create_pool(self.postgres_dsn)
        return self.pool
