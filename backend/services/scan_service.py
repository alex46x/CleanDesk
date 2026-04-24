"""
services/scan_service.py — Orchestrates scan sessions.

Responsible for:
  • Creating ScanSession records
  • Running FileScanner and persisting FileRecord rows in batches
  • Building the incremental cache from existing DB records
  • Emitting real-time progress via asyncio.Queue (WebSocket bridge)
"""

from __future__ import annotations

import asyncio
import logging
import time

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.scanner import FileInfo, FileScanner
from backend.database.models import FileRecord, ScanSession
from backend.schemas.schemas import ProgressEvent

logger = logging.getLogger(__name__)

_BATCH_SIZE = 500   # rows persisted per DB transaction


class ScanService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def start_scan(
        self,
        root_paths: list[str],
        *,
        incremental: bool = True,
        exclude_patterns: list[str] | None = None,
        progress_queue: asyncio.Queue | None = None,
    ) -> ScanSession:
        """
        Kick off a full or incremental scan.
        Returns the completed ScanSession ORM object.
        """
        session_rec = ScanSession(
            root_path=",".join(root_paths),
            started_at=time.time(),
            status="running",
        )
        self._db.add(session_rec)
        await self._db.flush()  # get ID without committing
        session_id = session_rec.id

        logger.info("Starting scan session %d on %s", session_id, root_paths)

        # Build incremental cache if requested
        cache: dict[str, tuple[float, int]] = {}
        if incremental:
            cache = await self._build_incremental_cache()
            logger.debug("Incremental cache loaded: %d entries", len(cache))

        try:
            total = await self._run_scanner(
                root_paths=root_paths,
                session_id=session_id,
                exclude_patterns=exclude_patterns or [],
                cache=cache,
                progress_queue=progress_queue,
            )

            session_rec.status = "done"
            session_rec.completed_at = time.time()
            session_rec.total_files = total
            await self._db.commit()
            logger.info("Scan session %d complete — %d files", session_id, total)

        except Exception as exc:
            session_rec.status = "failed"
            await self._db.commit()
            logger.error("Scan session %d failed: %s", session_id, exc)
            raise

        return session_rec

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _build_incremental_cache(self) -> dict[str, tuple[float, int]]:
        """Load path → (mtime, size) for all known files."""
        stmt = select(FileRecord.path, FileRecord.last_modified, FileRecord.size)
        result = await self._db.execute(stmt)
        return {
            row.path: (row.last_modified or 0.0, row.size or 0)
            for row in result.fetchall()
        }

    async def _run_scanner(
        self,
        root_paths: list[str],
        session_id: int,
        exclude_patterns: list[str],
        cache: dict[str, tuple[float, int]],
        progress_queue: asyncio.Queue | None,
    ) -> int:
        """
        Run scanner in a thread pool thread, batch-insert results via async DB.
        Returns total file count persisted.
        """
        loop = asyncio.get_running_loop()
        file_queue: asyncio.Queue[FileInfo | None] = asyncio.Queue(maxsize=2000)

        def _scan_thread() -> None:
            scanner = FileScanner(
                root_paths=root_paths,
                exclude_patterns=exclude_patterns,
                incremental_cache=cache,
            )
            try:
                for fi in scanner.scan():
                    asyncio.run_coroutine_threadsafe(file_queue.put(fi), loop).result()
            finally:
                asyncio.run_coroutine_threadsafe(file_queue.put(None), loop).result()

        scan_task = asyncio.create_task(asyncio.to_thread(_scan_thread))

        total = 0
        batch: list[FileInfo] = []

        while True:
            fi = await file_queue.get()
            if fi is None:
                break

            batch.append(fi)
            total += 1

            if len(batch) >= _BATCH_SIZE:
                await self._persist_batch(batch, session_id)
                if progress_queue:
                    await progress_queue.put(
                        ProgressEvent(
                            event="scan_progress",
                            session_id=session_id,
                            total_files=total,
                            processed=total,
                        )
                    )
                batch.clear()

        # Flush remaining
        if batch:
            await self._persist_batch(batch, session_id)

        await scan_task
        return total

    async def _persist_batch(
        self, batch: list[FileInfo], session_id: int
    ) -> None:
        """Upsert a batch of FileInfo rows."""
        rows = [
            {
                "path": fi.path,
                "name": fi.name,
                "extension": fi.extension,
                "size": fi.size,
                "category": fi.category,
                "last_modified": fi.last_modified,
                "scan_session_id": session_id,
            }
            for fi in batch
        ]

        # SQLite upsert (ON CONFLICT DO UPDATE)
        stmt = sqlite_insert(FileRecord).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["path"],
            set_={
                "name": stmt.excluded.name,
                "extension": stmt.excluded.extension,
                "size": stmt.excluded.size,
                "category": stmt.excluded.category,
                "last_modified": stmt.excluded.last_modified,
                "scan_session_id": stmt.excluded.scan_session_id,
            },
        )
        await self._db.execute(stmt)
        await self._db.flush()
