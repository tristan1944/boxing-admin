from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings


settings = get_settings()

engine_kwargs = {"future": True, "pool_pre_ping": True}
connect_args = {}
if settings.database_url.startswith("sqlite"):
    # Needed for SQLite when used with threads (FastAPI default)
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args, **engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


