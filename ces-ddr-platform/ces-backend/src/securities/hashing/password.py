import asyncio

import bcrypt


class PasswordGenerator:
    DUMMY_PASSWORD_HASH = "$2b$12$54aBIqJv7cs.HdP1GWJPueG0FQczMsnMJumQimx3AbKu3zo7EAPoq"

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

    def dummy_hash(self) -> str:
        return self.DUMMY_PASSWORD_HASH


def get_pwd_generator() -> PasswordGenerator:
    return PasswordGenerator()


pwd_generator: PasswordGenerator = get_pwd_generator()
