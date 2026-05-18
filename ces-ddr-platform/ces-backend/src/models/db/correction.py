from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.expression import text

from src.repository.table import Base

if TYPE_CHECKING:
    from src.models.db.ddr import DDR
    from src.models.db.occurrence import Occurrence
    from src.models.db.user import User


class Correction(Base):
    __tablename__ = "corrections"
    __table_args__ = (
        sqlalchemy.Index("idx_corrections_ddr_id", "ddr_id"),
        sqlalchemy.Index("idx_corrections_occurrence_id", "occurrence_id"),
        sqlalchemy.Index("idx_corrections_field_name_ddr_id", "field_name", "ddr_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    occurrence_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), sqlalchemy.ForeignKey("occurrences.id", ondelete="CASCADE"), nullable=False
    )
    ddr_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), sqlalchemy.ForeignKey("ddrs.id", ondelete="CASCADE"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(sqlalchemy.String(100), nullable=False)
    original_value: Mapped[str] = mapped_column(sqlalchemy.Text(), nullable=False)
    corrected_value: Mapped[str] = mapped_column(sqlalchemy.Text(), nullable=False)
    reason: Mapped[str] = mapped_column(sqlalchemy.Text(), nullable=False)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), sqlalchemy.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(
        sqlalchemy.BigInteger(),
        nullable=False,
        server_default=text("EXTRACT(EPOCH FROM now())::BIGINT"),
    )

    occurrence: Mapped["Occurrence"] = relationship(back_populates="corrections")
    ddr: Mapped["DDR"] = relationship(back_populates="corrections")
    user: Mapped["User"] = relationship()
