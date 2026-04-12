"""
api/routes/organize.py — File organization endpoints.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.websocket import ws_manager
from backend.database.connection import get_db
from backend.database.models import ScanSession
from backend.schemas.schemas import OrganizeRequest, OrganizeResponse, UndoRequest, UndoResponse
from backend.services.organize_service import OrganizeService

router = APIRouter(prefix="/organize", tags=["Organize"])


@router.post("/", response_model=OrganizeResponse)
async def organize_files(
    payload: OrganizeRequest,
    db: AsyncSession = Depends(get_db),
) -> OrganizeResponse:
    """Organize files from a scan session into category sub-folders."""
    session = await db.get(ScanSession, payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Scan session not found")

    progress_queue: asyncio.Queue = asyncio.Queue()

    async def _broadcast_progress() -> None:
        while True:
            event = await progress_queue.get()
            if event is None:
                break
            await ws_manager.broadcast(
                event.model_dump() if hasattr(event, "model_dump") else event
            )

    broadcast_task = asyncio.create_task(_broadcast_progress())

    service = OrganizeService(db)
    response = await service.organize(
        session_id=payload.session_id,
        destination_base=payload.destination_base,
        dry_run=payload.dry_run,
        categories=payload.categories,
        progress_queue=progress_queue,
    )

    await progress_queue.put(None)
    await broadcast_task

    await ws_manager.broadcast({"event": "organize_done", "dry_run": payload.dry_run})
    return response


@router.post("/undo", response_model=UndoResponse)
async def undo_moves(
    payload: UndoRequest,
    db: AsyncSession = Depends(get_db),
) -> UndoResponse:
    """Reverse file movements for the specified log IDs."""
    service = OrganizeService(db)
    return await service.undo(payload.log_ids)
