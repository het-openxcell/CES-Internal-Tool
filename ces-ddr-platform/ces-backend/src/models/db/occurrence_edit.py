from __future__ import annotations

import sqlalchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.expression import text

from src.repository.table import Base


class OccurrenceEdit(Base):
    __tablename__ = "occurrence_edits"
    __table_args__ = (
        sqlalchemy.Index("idx_occurrence_edits_ddr_id", "ddr_id"),
        sqlalchemy.Index("idx_occurrence_edits_occurrence_id", "occurrence_id"),
        sqlalchemy.Index("idx_occurrence_edits_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    occurrence_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), sqlalchemy.ForeignKey("occurrences.id", ondelete="CASCADE"), nullable=False
    )
    ddr_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), sqlalchemy.ForeignKey("ddrs.id", ondelete="CASCADE"), nullable=False
    )
    field: Mapped[str] = mapped_column(sqlalchemy.String(50), nullable=False)
    original_value: Mapped[str | None] = mapped_column(sqlalchemy.Text(), nullable=True)
    corrected_value: Mapped[str | None] = mapped_column(sqlalchemy.Text(), nullable=True)
    reason: Mapped[str | None] = mapped_column(sqlalchemy.Text(), nullable=True)
    created_by: Mapped[str | None] = mapped_column(sqlalchemy.Text(), nullable=True)
    created_at: Mapped[int] = mapped_column(sqlalchemy.BigInteger(), nullable=False)
