from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.expression import text

from src.repository.table import Base

if TYPE_CHECKING:
    from src.models.db.ddr import DDR, DDRDate


class CorrectionSummary(Base):
    __tablename__ = "correction_summaries"
    __table_args__ = (
        sqlalchemy.UniqueConstraint("ddr_date_id", "scope", name="uq_correction_summaries_date_scope"),
        sqlalchemy.Index("idx_correction_summaries_ddr_id", "ddr_id"),
        sqlalchemy.Index("idx_correction_summaries_ddr_date_id", "ddr_date_id"),
        sqlalchemy.Index("idx_correction_summaries_scope", "scope"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    ddr_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), sqlalchemy.ForeignKey("ddrs.id", ondelete="CASCADE"), nullable=False
    )
    ddr_date_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), sqlalchemy.ForeignKey("ddr_dates.id", ondelete="CASCADE"), nullable=False
    )
    scope: Mapped[str] = mapped_column(sqlalchemy.String(30), nullable=False)
    summary: Mapped[str] = mapped_column(sqlalchemy.Text(), nullable=False)
    source_logs: Mapped[list] = mapped_column(JSONB(), nullable=False, server_default=text("'[]'::jsonb"))
    edit_details: Mapped[list] = mapped_column(JSONB(), nullable=False, server_default=text("'[]'::jsonb"))
    correction_count: Mapped[int] = mapped_column(sqlalchemy.Integer(), nullable=False, server_default=text("0"))
    created_at: Mapped[int] = mapped_column(
        sqlalchemy.BigInteger(), nullable=False, server_default=text("EXTRACT(EPOCH FROM now())::BIGINT")
    )
    updated_at: Mapped[int] = mapped_column(
        sqlalchemy.BigInteger(), nullable=False, server_default=text("EXTRACT(EPOCH FROM now())::BIGINT")
    )

    ddr: Mapped[DDR] = relationship()
    ddr_date: Mapped[DDRDate] = relationship()

    @property
    def date(self) -> str | None:
        return self.ddr_date.date if self.ddr_date is not None else None
