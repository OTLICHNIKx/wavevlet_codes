"""SQLAlchemy-модель эксперимента."""

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ExperimentStatus(str, enum.Enum):
    queued = "queued"
    validating = "validating"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelling = "cancelling"
    cancelled = "cancelled"
    interrupted = "interrupted"


class Base(DeclarativeBase):
    pass


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    status: Mapped[ExperimentStatus] = mapped_column(
        Enum(ExperimentStatus),
        nullable=False,
        default=ExperimentStatus.queued,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Сериализованная runtime-конфигурация (JSON).
    config_json: Mapped[str] = mapped_column(Text, nullable=False)

    results_dir: Mapped[str] = mapped_column(String(512), nullable=False)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Текущий прогресс (обновляется из PROGRESS-строк subprocess'а).
    progress_completed: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)
    progress_payload: Mapped[str] = mapped_column(Text, default="{}")

    error_message: Mapped[str] = mapped_column(Text, default="")

    log_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")
