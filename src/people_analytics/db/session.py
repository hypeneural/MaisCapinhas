from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from people_analytics.core.settings import get_settings
from people_analytics.db.base import Base

engine = None
SessionLocal = None


def _init_engine() -> None:
    global engine, SessionLocal
    settings = get_settings()
    engine = create_engine(settings.database_url, future=True)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db() -> None:
    if engine is None:
        _init_engine()
    from people_analytics.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session():
    if engine is None:
        _init_engine()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
