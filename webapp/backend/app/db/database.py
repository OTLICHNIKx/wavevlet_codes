"""Инициализация SQLite и фабрика сессий."""

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DB_PATH, PRESETS_DIR, WEBAPP_DATA_ROOT
from app.models.experiment import Base


def init_directories() -> None:
    WEBAPP_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)


init_directories()

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def _migrate_experiments_table() -> None:
    """
    Лёгкая ручная миграция для уже существующих баз данных:
    ``create_all`` не добавляет колонки в уже существующие таблицы,
    поэтому новые поля добавляются вручную после создания таблиц.
    """
    inspector = inspect(engine)
    if "experiments" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("experiments")
    }

    statements = []
    if "source" not in existing_columns:
        statements.append(
            "ALTER TABLE experiments "
            "ADD COLUMN source VARCHAR(32) NOT NULL DEFAULT 'local'"
        )
    if "original_filename" not in existing_columns:
        statements.append(
            "ALTER TABLE experiments "
            "ADD COLUMN original_filename VARCHAR(255) NOT NULL DEFAULT ''"
        )

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_experiments_table()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Создаём таблицы до импорта менеджера subprocess'ов.
init_db()
