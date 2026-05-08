from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.expression import text

from src.repository.table import Base

if TYPE_CHECKING:
    from src.models.db.ddr import DDR, DDRDate


class Occurrence(Base):
    __tablename__ = "occurrences"
    __table_args__ = (
        sqlalchemy.Index("idx_occurrences_ddr_id", "ddr_id"),
        sqlalchemy.Index("idx_occurrences_type", "type"),
        sqlalchemy.Index("idx_occurrences_date", "date"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    ddr_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), sqlalchemy.ForeignKey("ddrs.id", ondelete="CASCADE"), nullable=False
    )
    ddr_date_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), sqlalchemy.ForeignKey("ddr_dates.id", ondelete="CASCADE"), nullable=False
    )
    well_name: Mapped[str | None] = mapped_column(sqlalchemy.Text(), nullable=True)
    surface_location: Mapped[str | None] = mapped_column(sqlalchemy.Text(), nullable=True)
    type: Mapped[str] = mapped_column(sqlalchemy.String(100), nullable=False)
    section: Mapped[str | None] = mapped_column(sqlalchemy.String(20), nullable=True)
    mmd: Mapped[float | None] = mapped_column(sqlalchemy.Float(), nullable=True)
    density: Mapped[float | None] = mapped_column(sqlalchemy.Float(), nullable=True)
    notes: Mapped[str | None] = mapped_column(sqlalchemy.Text(), nullable=True)
    date: Mapped[str | None] = mapped_column(sqlalchemy.String(8), nullable=True)
    is_exported: Mapped[bool] = mapped_column(sqlalchemy.Boolean(), nullable=False, server_default=text("false"))
    created_at: Mapped[int] = mapped_column(sqlalchemy.BigInteger(), nullable=False)
    updated_at: Mapped[int] = mapped_column(sqlalchemy.BigInteger(), nullable=False)

    ddr: Mapped[DDR] = relationship(back_populates="occurrences")
    ddr_date: Mapped[DDRDate] = relationship(back_populates="occurrences")
