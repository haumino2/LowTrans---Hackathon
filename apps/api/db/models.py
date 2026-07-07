"""Database models — Postgres + pgvector when DATABASE_URL is set."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from pathlib import Path

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None  # type: ignore[misc, assignment]

DATABASE_URL = os.getenv("DATABASE_URL", "")
SQLITE_PATH = os.getenv("SQLITE_PATH", str(Path(__file__).resolve().parents[3] / "data" / "lowtrans.db"))


def _resolve_database_url() -> str:
    if os.getenv("USE_DB", "true").lower() == "false":
        return ""
    if DATABASE_URL:
        return DATABASE_URL
    return f"sqlite:///{SQLITE_PATH}"


engine = None
SessionLocal = None
_db_ready = False
_using_sqlite = False


class Base(DeclarativeBase):
    pass


class CopilotSessionRow(Base):
    __tablename__ = "copilot_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    alert_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertRow(Base):
    __tablename__ = "alerts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ResolvedCaseRow(Base):
    __tablename__ = "resolved_cases"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    document: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1024) if Vector else JSON, nullable=True
    )


class AuditRow(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TransactionRow(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    customer_id: Mapped[str] = mapped_column(String(64))
    customer_name: Mapped[str] = mapped_column(String(128))
    partner: Mapped[str] = mapped_column(String(128))
    asset: Mapped[str] = mapped_column(String(16))
    network: Mapped[str] = mapped_column(String(32))
    direction: Mapped[str] = mapped_column(String(16))
    amount_usd: Mapped[float] = mapped_column()
    kyt_score: Mapped[int] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String(16))
    travel_rule_status: Mapped[str] = mapped_column(String(32))
    country: Mapped[str] = mapped_column(String(64))
    rules_fired_count: Mapped[int] = mapped_column(Integer, default=0)
    mixer_exposure: Mapped[bool] = mapped_column(default=False)
    sanctions_hit: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime)


def init_db() -> bool:
    """Create tables. Tries Postgres first, falls back to SQLite file."""
    global engine, SessionLocal, _db_ready, _using_sqlite
    url = _resolve_database_url()
    if not url:
        return False

    candidates = [url]
    if url.startswith("postgresql"):
        candidates.append(f"sqlite:///{SQLITE_PATH}")

    for candidate in candidates:
        try:
            eng = create_engine(candidate, pool_pre_ping=True)
            with eng.connect() as conn:
                if candidate.startswith("postgresql"):
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                    conn.commit()
            Base.metadata.create_all(eng)
            engine = eng
            SessionLocal = sessionmaker(bind=engine)
            _db_ready = True
            _using_sqlite = candidate.startswith("sqlite")
            return True
        except Exception:
            continue

    engine = None
    SessionLocal = None
    _db_ready = False
    _using_sqlite = False
    return False


def is_sqlite() -> bool:
    return _using_sqlite


def is_db_ready() -> bool:
    return _db_ready


def get_session():
    if not SessionLocal:
        raise RuntimeError("Database not initialized")
    return SessionLocal()
