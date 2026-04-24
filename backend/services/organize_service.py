"""
services/organize_service.py — Orchestrates file organization with full logging.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.mover import FileMover, MoveRequest, MoveResult, UndoManager
from backend.database.models import FileRecord, Log, UndoHistory
from backend.schemas.schemas import (
    OrganizeResultItem,
    OrganizeResponse,
    ProgressEvent,
    UndoResultItem,
    UndoResponse,
)

logger = logging.getLogger(__name__)


class OrganizeService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def organize(
        self,
        session_id: int,
        destination_base: str,
        *,
        dry_run: bool = False,
        categories: list[str] | None = None,
        progress_queue: asyncio.Queue | None = None,
    ) -> OrganizeResponse:
        """Organize all files from a scan session into category sub-folders."""
        stmt = select(FileRecord).where(FileRecord.scan_session_id == session_id)
        if categories:
            stmt = stmt.where(FileRecord.category.in_(categories))

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total_files = int((await self._db.execute(total_stmt)).scalar_one())
        file_stream = await self._db.stream_scalars(stmt.execution_options(yield_per=200))

        logger.info(
            "Organizing %d files (dry_run=%s, dest=%s)",
            total_files,
            dry_run,
            destination_base,
        )

        mover = FileMover()
        results: list[OrganizeResultItem] = []
        succeeded = 0
        failed = 0

        async for i, file_rec in _async_enumerate(file_stream):
            category = file_rec.category or "Others"
            dest_dir = str(Path(destination_base) / category)

            req = MoveRequest(
                source=file_rec.path,
                destination_dir=dest_dir,
                dry_run=dry_run,
            )

            move_result: MoveResult = await asyncio.to_thread(mover.move, req)

            item = OrganizeResultItem(
                source=move_result.source,
                destination=move_result.destination,
                success=move_result.success,
                error=move_result.error,
                was_renamed=move_result.was_renamed,
                dry_run=dry_run,
            )
            results.append(item)

            if move_result.success:
                succeeded += 1
                if not dry_run:
                    await self._log_move(file_rec, move_result, session_id)
            else:
                failed += 1
                await self._log_failure(file_rec, move_result, session_id)

            if not dry_run and (i + 1) % 200 == 0:
                await self._db.flush()

            if progress_queue and (i + 1) % 50 == 0:
                await progress_queue.put(
                    ProgressEvent(
                        event="organize_progress",
                        session_id=session_id,
                        total_files=total_files,
                        processed=i + 1,
                    )
                )

        await self._db.commit()

        return OrganizeResponse(
            total=total_files,
            succeeded=succeeded,
            failed=failed,
            dry_run=dry_run,
            results=results,
        )

    async def undo(self, log_ids: list[int]) -> UndoResponse:
        """Reverse file movements for the given log IDs."""
        stmt = (
            select(Log, UndoHistory)
            .join(UndoHistory, UndoHistory.log_id == Log.id)
            .where(Log.id.in_(log_ids))
            .where(UndoHistory.can_undo == True)  # noqa: E712
        )
        result = await self._db.execute(stmt)
        rows = result.all()

        undo_mgr = UndoManager()
        results: list[UndoResultItem] = []
        succeeded = 0
        failed = 0

        for log, undo_rec in rows:
            move_result = await asyncio.get_running_loop().run_in_executor(
                None,
                undo_mgr.undo_move,
                undo_rec.original_path,
                log.new_path,
            )

            if move_result.success:
                undo_rec.can_undo = False
                undo_rec.undone_at = time.time()
                log.status = "undone"
                succeeded += 1
                results.append(
                    UndoResultItem(
                        log_id=log.id,
                        original_path=undo_rec.original_path,
                        current_path=move_result.destination,
                        success=True,
                    )
                )
            else:
                failed += 1
                results.append(
                    UndoResultItem(
                        log_id=log.id,
                        original_path=undo_rec.original_path,
                        current_path=log.new_path,
                        success=False,
                        error=move_result.error,
                    )
                )

        await self._db.commit()
        return UndoResponse(
            total=len(rows),
            succeeded=succeeded,
            failed=failed,
            results=results,
        )

    # ------------------------------------------------------------------

    async def _log_move(
        self,
        file_rec: FileRecord,
        move_result: MoveResult,
        session_id: int,
    ) -> None:
        log = Log(
            old_path=file_rec.path,
            new_path=move_result.destination,
            operation="move",
            status="success",
            session_id=session_id,
        )
        log.undo_entry = UndoHistory(
            original_path=file_rec.path,
            can_undo=True,
        )
        self._db.add(log)

        # Update file record
        file_rec.path = move_result.destination
        file_rec.name = Path(move_result.destination).name

    async def _log_failure(
        self,
        file_rec: FileRecord,
        move_result: MoveResult,
        session_id: int,
    ) -> None:
        log = Log(
            old_path=file_rec.path,
            new_path=move_result.destination,
            operation="move",
            status="failed",
            session_id=session_id,
            error_message=move_result.error,
        )
        self._db.add(log)


async def _async_enumerate(iterable, start: int = 0):
    index = start
    async for item in iterable:
        yield index, item
        index += 1
