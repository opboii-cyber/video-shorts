"""
database.py — Database Configuration & Session Management
===========================================================

Uses SQLAlchemy async with:
  • SQLite for development (zero config)
  • PostgreSQL for production (via DATABASE_URL env var)
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

# Use Postgres in production, SQLite in dev
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./video_shorts.db"
)

# Handle SQLite-specific args
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables — call on startup."""
    Base.metadata.create_all(bind=engine)
