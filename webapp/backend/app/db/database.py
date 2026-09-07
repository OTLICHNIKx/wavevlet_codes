"""Инициализация SQLite и фабрика сессий."""

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DB_PATH, PRESETS_DIR, WEBAPP_DATA_ROOT
from app.models.experiment import Base, CustomPreset


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
    _migrate_legacy_presets()


def _migrate_legacy_presets() -> None:
    """Однократно переносит старые JSON-пресеты в SQLite."""
    import json
    import uuid
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with SessionLocal() as session:
        for path in sorted(PRESETS_DIR.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                name = str(data["name"]).strip()
                config = data["config"]
            except (OSError, KeyError, TypeError, json.JSONDecodeError):
                continue
            if not name or not isinstance(config, dict):
                continue
            legacy_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"wavelet-preset:{path.stem}"))
            if session.get(CustomPreset, legacy_id) is not None:
                continue
            session.add(
                CustomPreset(
                    id=legacy_id,
                    name=name,
                    description=str(data.get("description", "")),
                    created_at=now,
                    updated_at=now,
                    config_json=json.dumps(config, ensure_ascii=False),
                    schema_version=1,
                )
            )
        session.commit()


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
