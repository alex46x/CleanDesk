"""
database/models.py — SQLAlchemy ORM models.

Designed to be PostgreSQL-compatible from day one (no SQLite-only types).
Primary keys use Integer; swap to UUID for PostgreSQL as desired.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> float:
    return datetime.now(timezone.utc).timestamp()


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Scan sessions
# ---------------------------------------------------------------------------
class ScanSession(Base):
    __tablename__ = "scan_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    root_path: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[float | None] = mapped_column(Float)
    completed_at: Mapped[float | None] = mapped_column(Float)
    total_files: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|running|done|failed

    files: Mapped[list[FileRecord]] = relationship(
        "FileRecord", back_populates="session", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<ScanSession id={self.id} root={self.root_path!r} status={self.status}>"


# ---------------------------------------------------------------------------
# File index
# ---------------------------------------------------------------------------
class FileRecord(Base):
    __tablename__ = "files"
    __table_args__ = (
        Index("ix_files_path", "path", unique=True),
        Index("ix_files_scan_session_id", "scan_session_id"),
        Index("ix_files_session_category", "scan_session_id", "category"),
        Index("ix_files_category", "category"),
        Index("ix_files_extension", "extension"),
        Index("ix_files_size", "size"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    extension: Mapped[str | None] = mapped_column(String(32))
    size: Mapped[int | None] = mapped_column(Integer)
    category: Mapped[str | None] = mapped_column(String(64))
    last_modified: Mapped[float | None] = mapped_column(Float)
    hash: Mapped[str | None] = mapped_column(String(64))         # xxhash hex
    scan_session_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("scan_sessions.id", ondelete="SET NULL")
    )
    created_at: Mapped[float] = mapped_column(Float, default=_utcnow)

    session: Mapped[ScanSession | None] = relationship(
        "ScanSession", back_populates="files"
    )

    def __repr__(self) -> str:
        return f"<FileRecord id={self.id} name={self.name!r} cat={self.category}>"


# ---------------------------------------------------------------------------
# Movement logs
# ---------------------------------------------------------------------------
class Log(Base):
    __tablename__ = "logs"
    __table_args__ = (
        Index("ix_logs_timestamp", "timestamp"),
        Index("ix_logs_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    old_path: Mapped[str] = mapped_column(Text, nullable=False)
    new_path: Mapped[str] = mapped_column(Text, nullable=False)
    operation: Mapped[str] = mapped_column(String(16), nullable=False)  # move|copy|delete
    status: Mapped[str] = mapped_column(String(16), nullable=False)     # success|failed|undone
    timestamp: Mapped[float] = mapped_column(Float, default=_utcnow)
    session_id: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)

    undo_entry: Mapped[UndoHistory | None] = relationship(
        "UndoHistory", back_populates="log", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Log id={self.id} op={self.operation} status={self.status}>"


# ---------------------------------------------------------------------------
# Undo history
# ---------------------------------------------------------------------------
class UndoHistory(Base):
    __tablename__ = "undo_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    log_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("logs.id", ondelete="CASCADE"), unique=True
    )
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    can_undo: Mapped[bool] = mapped_column(Boolean, default=True)
    undone_at: Mapped[float | None] = mapped_column(Float)

    log: Mapped[Log] = relationship("Log", back_populates="undo_entry")


# ---------------------------------------------------------------------------
# Custom classification rules
# ---------------------------------------------------------------------------
class Rule(Base):
    __tablename__ = "rules"
    __table_args__ = (Index("ix_rules_priority", "priority"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    pattern: Mapped[str] = mapped_column(Text, nullable=False)    # glob or regex
    match_type: Mapped[str] = mapped_column(String(16), default="glob")  # glob|regex|extension
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    target_folder: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[float] = mapped_column(Float, default=_utcnow)

    def __repr__(self) -> str:
        return f"<Rule id={self.id} name={self.name!r} cat={self.category}>"
