"""SQLAlchemy engine/session. PostgreSQL (pg8000) in production, SQLite for local dev and tests."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import JSON, create_engine, inspect, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

log = logging.getLogger(__name__)

# JSONB on PostgreSQL, portable JSON elsewhere.
JSONType = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_factory: sessionmaker[Session] | None = None


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url or url in ("sqlite://", "sqlite:///"):
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)


def get_engine() -> Engine:
    global _engine, _factory
    if _engine is None:
        _engine = make_engine(get_settings().database_url)
        _factory = sessionmaker(_engine, expire_on_commit=False)
    return _engine


def reset_engine() -> None:
    """Drop the cached engine (tests, and Celery worker processes after fork)."""
    global _engine, _factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _factory = None


@contextmanager
def session_scope() -> Iterator[Session]:
    get_engine()
    assert _factory is not None
    session = _factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency."""
    with session_scope() as session:
        yield session


def _add_missing_columns() -> None:
    """create_all never alters existing tables: add nullable columns introduced after a volume
    was first created (keeps `docker compose up` working without wiping data)."""
    engine = get_engine()
    inspector = inspect(engine)
    for table in Base.metadata.sorted_tables:
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name not in existing and column.nullable:
                kind = column.type.compile(engine.dialect)
                ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {kind}'
                with engine.begin() as connection:
                    connection.execute(text(ddl))
                log.info("added column", extra={"table": table.name, "column": column.name})


def init_db(attempts: int = 30, delay: float = 2.0) -> None:
    """create_all with retries: the DB may still be starting, and api/worker/beat may race."""
    from app import models  # noqa: F401  (register tables)

    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            engine = get_engine()
            with engine.begin() as connection:
                if engine.dialect.name == "postgresql":
                    # api, worker and beat start together: only one of them creates the schema at a time
                    connection.execute(text("SELECT pg_advisory_xact_lock(74210011)"))
                Base.metadata.create_all(connection)
            _add_missing_columns()
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            log.log(
                logging.INFO if attempt < 5 else logging.WARNING,
                "waiting for database",
                extra={"attempt": attempt, "error": type(exc).__name__},
            )
            time.sleep(delay)
    raise RuntimeError("database unavailable") from last
