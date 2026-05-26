import sqlalchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.repository.table import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=sqlalchemy.text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(sqlalchemy.String(length=100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(sqlalchemy.Text(), nullable=True)
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


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        sqlalchemy.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        sqlalchemy.ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
