from fastapi import Depends

from src.models.db.user import User
from src.securities.authorizations.jwt_authentication import jwt_authentication
from src.utilities.exceptions.exceptions import ForbiddenException


class RoleChecker:
    def __init__(self, allowed_roles: list[str]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(jwt_authentication)) -> User:
        user_roles = [r.name for r in getattr(current_user, "roles", [])]
        if not any(role in user_roles for role in self.allowed_roles):
            raise ForbiddenException("insufficient_role")
        return current_user


admin_only = RoleChecker(["ADMIN"])
user_only = RoleChecker(["USER"])
admin_or_user = RoleChecker(["ADMIN", "USER"])
