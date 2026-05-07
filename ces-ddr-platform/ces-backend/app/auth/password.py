import asyncio

import bcrypt


class PasswordVerifier:
    DUMMY_PASSWORD_HASH = "$2a$10$7EqJtq98hPqEX7fNZaFWoOhiZCQGNuCIlnLzKeE/d1qFJKZ0f4uTe"

    async def verify(self, password: str, password_hash: str) -> bool:
        return await asyncio.to_thread(self.verify_sync, password, password_hash)

    async def hash(self, password: str) -> str:
        return await asyncio.to_thread(self.hash_sync, password)

    def verify_sync(self, password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except ValueError:
            return False

    def hash_sync(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def dummy_hash(self) -> str:
        return self.DUMMY_PASSWORD_HASH
