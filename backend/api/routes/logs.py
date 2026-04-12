"""
api/routes/logs.py — Log retrieval endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.connection import get_db
from backend.database.models import Log
from backend.schemas.schemas import LogResponse

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("/", response_model=list[LogResponse])
async def list_logs(
    status: str | None = Query(None, description="Filter by status: success|failed|undone"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[LogResponse]:
    stmt = select(Log).order_by(desc(Log.timestamp)).offset(offset).limit(limit)
    if status:
        stmt = stmt.where(Log.status == status)
    result = await db.execute(stmt)
    return [LogResponse.model_validate(row) for row in result.scalars().all()]
