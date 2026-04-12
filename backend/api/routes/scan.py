"""
api/routes/scan.py — Scan-related REST endpoints.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.websocket import websocket_endpoint, ws_manager
from backend.database.connection import get_db
from backend.database.models import FileRecord, ScanSession
from backend.schemas.schemas import (
    FileInfoResponse,
    ProgressEvent,
    ScanRequest,
    ScanSessionResponse,
)
from backend.services.scan_service import ScanService

router = APIRouter(prefix="/scan", tags=["Scan"])


@router.post("/start", response_model=ScanSessionResponse, status_code=202)
async def start_scan(
    payload: ScanRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ScanSessionResponse:
    """Kick off a background scan and return the session stub immediately."""
    service = ScanService(db)
    progress_queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()

    async def _run() -> None:
        try:
            await service.start_scan(
                root_paths=payload.root_paths,
                incremental=payload.incremental,
                exclude_patterns=payload.exclude_patterns,
                progress_queue=progress_queue,
            )
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


@router.get("/sessions/{session_id}/files", response_model=list[FileInfoResponse])
async def list_files(
    session_id: int,
    category: str | None = None,
    limit: int = 200,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[FileInfoResponse]:
    stmt = (
        select(FileRecord)
        .where(FileRecord.scan_session_id == session_id)
        .offset(offset)
        .limit(min(limit, 1000))
    )
    if category:
        stmt = stmt.where(FileRecord.category == category)
    result = await db.execute(stmt)
    files = result.scalars().all()
    return [FileInfoResponse.model_validate(f) for f in files]


@router.websocket("/ws/progress")
async def scan_ws(websocket: WebSocket) -> None:
    """WebSocket: server pushes scan progress to this client."""
    queue: asyncio.Queue = asyncio.Queue()
    await websocket_endpoint(websocket, queue)
