from decimal import Decimal
from typing import TYPE_CHECKING

import sqlalchemy
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from src.models.db.occurrence import Occurrence

from src.repository.table import Base


class DDR(Base):
    __tablename__ = "ddrs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=sqlalchemy.text("gen_random_uuid()"),
    )
    file_path: Mapped[str] = mapped_column(sqlalchemy.Text(), nullable=False)
    status: Mapped[str] = mapped_column(
        sqlalchemy.String(length=20),
        nullable=False,
        server_default=sqlalchemy.text("'queued'"),
    )
    well_name: Mapped[str | None] = mapped_column(sqlalchemy.Text(), nullable=True)
    surface_location: Mapped[str | None] = mapped_column(sqlalchemy.Text(), nullable=True)
    created_at: Mapped[int] = mapped_column(sqlalchemy.BigInteger(), nullable=False)
    updated_at: Mapped[int] = mapped_column(sqlalchemy.BigInteger(), nullable=False)

    dates: Mapped[list["DDRDate"]] = relationship(back_populates="ddr")
    queue_entries: Mapped[list["ProcessingQueue"]] = relationship(back_populates="ddr")
    occurrences: Mapped[list["Occurrence"]] = relationship(back_populates="ddr")


class DDRDate(Base):
    __tablename__ = "ddr_dates"
    __table_args__ = (sqlalchemy.Index("idx_ddr_dates_ddr_id", "ddr_id"),)

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=sqlalchemy.text("gen_random_uuid()"),
    )
    ddr_id: Mapped[str] = mapped_column(UUID(as_uuid=False), sqlalchemy.ForeignKey("ddrs.id"), nullable=False)
    date: Mapped[str] = mapped_column(sqlalchemy.String(length=8), nullable=False)
    status: Mapped[str] = mapped_column(sqlalchemy.String(length=20), nullable=False)
    raw_response: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    final_json: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    error_log: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)
    created_at: Mapped[int] = mapped_column(sqlalchemy.BigInteger(), nullable=False)
    updated_at: Mapped[int] = mapped_column(sqlalchemy.BigInteger(), nullable=False)

    ddr: Mapped[DDR] = relationship(back_populates="dates")
    pipeline_runs: Mapped[list["PipelineRun"]] = relationship(back_populates="ddr_date")
    occurrences: Mapped[list["Occurrence"]] = relationship(back_populates="ddr_date")


class ProcessingQueue(Base):
    __tablename__ = "processing_queue"
    __table_args__ = (
        sqlalchemy.Index("idx_processing_queue_ddr_id", "ddr_id"),
        sqlalchemy.UniqueConstraint("position", name="uq_processing_queue_position"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=sqlalchemy.text("gen_random_uuid()"),
    )
    ddr_id: Mapped[str] = mapped_column(UUID(as_uuid=False), sqlalchemy.ForeignKey("ddrs.id"), nullable=False)
    position: Mapped[int] = mapped_column(sqlalchemy.Integer(), nullable=False)
    created_at: Mapped[int] = mapped_column(sqlalchemy.BigInteger(), nullable=False)

    ddr: Mapped[DDR] = relationship(back_populates="queue_entries")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=sqlalchemy.text("gen_random_uuid()"),
    )
    ddr_date_id: Mapped[str] = mapped_column(UUID(as_uuid=False), sqlalchemy.ForeignKey("ddr_dates.id"), nullable=False)
    gemini_input_tokens: Mapped[int | None] = mapped_column(sqlalchemy.Integer(), nullable=True)
    gemini_output_tokens: Mapped[int | None] = mapped_column(sqlalchemy.Integer(), nullable=True)
    cost_usd: Mapped[Decimal | None] = mapped_column(sqlalchemy.Numeric(10, 6), nullable=True)
    created_at: Mapped[int] = mapped_column(sqlalchemy.BigInteger(), nullable=False)

    ddr_date: Mapped[DDRDate] = relationship(back_populates="pipeline_runs")
