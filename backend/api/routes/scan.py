"""
api/routes/scan.py — Scan-related REST endpoints.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.websocket import websocket_endpoint, ws_manager
from backend.database.connection import get_db, AsyncSessionLocal
from backend.database.models import FileRecord, ScanSession
from backend.schemas.schemas import (
    FileListResponse,
    FileInfoResponse,
    ProgressEvent,
    ScanRequest,
    ScanSessionResponse,
    SessionStatsResponse,
)
from backend.services.scan_service import ScanService

router = APIRouter(prefix="/scan", tags=["Scan"])


@router.post("/start", response_model=ScanSessionResponse, status_code=202)
async def start_scan(
    payload: ScanRequest,
    background_tasks: BackgroundTasks,
) -> ScanSessionResponse:
    """Kick off a background scan and return the session stub immediately."""
    progress_queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()

    async def _run() -> None:
        async with AsyncSessionLocal() as session_db:
            service = ScanService(session_db)
            try:
                await service.start_scan(
                    root_paths=payload.root_paths,
                    incremental=payload.incremental,
                    exclude_patterns=payload.exclude_patterns,
                    progress_queue=progress_queue,
                )
            except Exception:
                await ws_manager.broadcast({"event": "scan_done", "error": True})
            finally:
                await progress_queue.put(None)  # signal done
                await ws_manager.broadcast({"event": "scan_done"})

    background_tasks.add_task(_run)

    # Return a placeholder session response
    return ScanSessionResponse(
        id=-1,
        root_path=",".join(payload.root_paths),
        started_at=None,
        completed_at=None,
        total_files=None,
        status="started",
    )


@router.get("/sessions", response_model=list[ScanSessionResponse])
async def list_sessions(db: AsyncSession = Depends(get_db)) -> list[ScanSessionResponse]:
    result = await db.execute(select(ScanSession).order_by(ScanSession.id.desc()))
    sessions = result.scalars().all()
    return [ScanSessionResponse.model_validate(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=ScanSessionResponse)
async def get_session(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> ScanSessionResponse:
    session = await db.get(ScanSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return ScanSessionResponse.model_validate(session)


@router.get("/sessions/{session_id}/files", response_model=FileListResponse)
async def list_files(
    session_id: int,
    category: str | None = None,
    search: str | None = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    limit: int = 200,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> FileListResponse:
    base_stmt = select(FileRecord).where(FileRecord.scan_session_id == session_id)
    if category:
        base_stmt = base_stmt.where(FileRecord.category == category)
    if search:
        like_query = f"%{search.strip()}%"
        base_stmt = base_stmt.where(
            or_(
                FileRecord.name.ilike(like_query),
                FileRecord.path.ilike(like_query),
            )
        )

    sort_map = {
        "name": FileRecord.name,
        "size": FileRecord.size,
        "category": FileRecord.category,
        "last_modified": FileRecord.last_modified,
        "path": FileRecord.path,
    }
    sort_column = sort_map.get(sort_by, FileRecord.name)
    order_fn = desc if sort_order.lower() == "desc" else asc

    total_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = int((await db.execute(total_stmt)).scalar_one())

    stmt = (
        base_stmt.order_by(order_fn(sort_column), asc(FileRecord.id))
        .offset(max(offset, 0))
        .limit(min(max(limit, 1), 1000))
    )
    result = await db.execute(stmt)
    files = result.scalars().all()
    return FileListResponse(
        items=[FileInfoResponse.model_validate(f) for f in files],
        total=total,
        limit=min(max(limit, 1), 1000),
        offset=max(offset, 0),
    )


@router.get("/sessions/{session_id}/stats", response_model=SessionStatsResponse)
async def get_session_stats(
    session_id: int,
    db: AsyncSession = Depends(get_db),
) -> SessionStatsResponse:
    session = await db.get(ScanSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    total_stmt = select(func.count()).where(FileRecord.scan_session_id == session_id)
    total_files = int((await db.execute(total_stmt)).scalar_one())

    category_stmt = (
        select(FileRecord.category, func.count())
        .where(FileRecord.scan_session_id == session_id)
        .group_by(FileRecord.category)
    )
    category_rows = (await db.execute(category_stmt)).all()
    categories = {(category or "Others"): count for category, count in category_rows}

    return SessionStatsResponse(
        session_id=session_id,
        total_files=total_files,
        categories=categories,
    )


@router.websocket("/ws/progress")
async def scan_ws(websocket: WebSocket) -> None:
    """WebSocket: server pushes scan progress to this client."""
    queue: asyncio.Queue = asyncio.Queue()
    await websocket_endpoint(websocket, queue)
