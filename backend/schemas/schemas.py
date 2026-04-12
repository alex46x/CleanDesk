"""
schemas/schemas.py — Pydantic v2 request/response schemas.

Kept separate from ORM models to maintain a clean API boundary.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    root_paths: list[str] = Field(..., min_length=1, description="Paths to scan")
    incremental: bool = Field(True, description="Skip unchanged files")
    exclude_patterns: list[str] = Field(default_factory=list)

    @field_validator("root_paths")
    @classmethod
    def paths_not_empty(cls, v: list[str]) -> list[str]:
        if any(not p.strip() for p in v):
            raise ValueError("Paths must not be empty strings")
        return [p.strip() for p in v]


class ScanSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    root_path: str
    started_at: Optional[float]
    completed_at: Optional[float]
    total_files: Optional[int]
    status: str


class FileInfoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str
    name: str
    extension: Optional[str]
    size: Optional[int]
    category: Optional[str]
    last_modified: Optional[float]
    hash: Optional[str]
    scan_session_id: Optional[int]


# ---------------------------------------------------------------------------
# Organize
# ---------------------------------------------------------------------------

class OrganizeRequest(BaseModel):
    session_id: int = Field(..., description="Scan session whose files to organize")
    destination_base: str = Field(..., description="Root folder for organized output")
    dry_run: bool = Field(False, description="Preview only — no files are moved")
    categories: Optional[list[str]] = Field(
        None, description="Limit to these categories; None = all"
    )


class OrganizeResultItem(BaseModel):
    source: str
    destination: str
    success: bool
    error: Optional[str] = None
    was_renamed: bool = False
    dry_run: bool = False


class OrganizeResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    dry_run: bool
    results: list[OrganizeResultItem]


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

class RuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    pattern: str = Field(..., min_length=1)
    match_type: str = Field("glob", pattern="^(glob|regex|extension)$")
    category: str = Field(..., min_length=1, max_length=64)
    target_folder: str = Field(..., min_length=1)
    priority: int = Field(0, ge=0, le=1000)
    enabled: bool = True


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    pattern: Optional[str] = None
    match_type: Optional[str] = None
    category: Optional[str] = None
    target_folder: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class RuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    pattern: str
    match_type: str
    category: str
    target_folder: str
    priority: int
    enabled: bool
    created_at: float


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

class LogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    old_path: str
    new_path: str
    operation: str
    status: str
    timestamp: float
    session_id: Optional[int]
    error_message: Optional[str]


# ---------------------------------------------------------------------------
# Undo
# ---------------------------------------------------------------------------

class UndoRequest(BaseModel):
    log_ids: list[int] = Field(..., min_length=1)


class UndoResultItem(BaseModel):
    log_id: int
    original_path: str
    current_path: str
    success: bool
    error: Optional[str] = None


class UndoResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: list[UndoResultItem]


# ---------------------------------------------------------------------------
# WebSocket progress events
# ---------------------------------------------------------------------------

class ProgressEvent(BaseModel):
    event: str          # "scan_progress" | "organize_progress" | "done" | "error"
    session_id: Optional[int] = None
    total_files: int = 0
    processed: int = 0
    files_per_second: float = 0.0
    message: Optional[str] = None
    payload: Optional[Any] = None
