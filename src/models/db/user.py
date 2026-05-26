import sqlalchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repository.table import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=sqlalchemy.text("gen_random_uuid()"),
    )
    username: Mapped[str] = mapped_column(sqlalchemy.String(length=255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(sqlalchemy.Text(), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        sqlalchemy.Boolean(),
        nullable=False,
        server_default=sqlalchemy.true(),
    )
    created_at: Mapped[int] = mapped_column(
        sqlalchemy.BigInteger(),
        nullable=False,
        server_default=sqlalchemy.text("EXTRACT(EPOCH FROM now())::BIGINT"),
    )
    updated_at: Mapped[int] = mapped_column(
        sqlalchemy.BigInteger(),
        nullable=False,
        server_default=sqlalchemy.text("EXTRACT(EPOCH FROM now())::BIGINT"),
    )

    roles: Mapped[list["Role"]] = relationship(  # noqa: F821
        "Role", secondary="user_roles", lazy="noload"
    )
