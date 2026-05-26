import asyncio

import bcrypt


class PasswordGenerator:
    _DUMMY_HASH = "$2b$12$ugrU2DLrcp6QoLBOh2pnUe96x25t1ZGJEUfXc2/eRS41SsRsi.HFi"

    def dummy_hash(self) -> str:
        return self._DUMMY_HASH

    async def generate_hashed_password(self, password: str) -> str:
        return await asyncio.to_thread(self.generate_hashed_password_sync, password)

    def generate_hashed_password_sync(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    async def is_password_authenticated(self, password: str, hashed_password: str) -> bool:
        return await asyncio.to_thread(self.is_password_authenticated_sync, password, hashed_password)

    def is_password_authenticated_sync(self, password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode(), hashed_password.encode())
        except ValueError:
            return False


def get_pwd_generator() -> PasswordGenerator:
    return PasswordGenerator()


pwd_generator: PasswordGenerator = get_pwd_generator()
