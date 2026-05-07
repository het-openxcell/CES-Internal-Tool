from src.models.db.user import User
from src.repository.crud.base import BaseCRUDRepository, ModelType
from src.repository.crud.user import UserCRUDRepository
from src.repository.database import AsyncDatabase


def test_base_crud_repository_uses_model_typevar() -> None:
    assert ModelType.__name__ == "ModelType"
    assert issubclass(UserCRUDRepository, BaseCRUDRepository)
    assert UserCRUDRepository.model is User


def test_database_exposes_session_factory() -> None:
    assert hasattr(AsyncDatabase, "get_session")
