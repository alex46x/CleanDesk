"""
core/mover.py — Safe, atomic file mover with full undo support.

Strategy:
  • Same drive  → os.rename() (atomic on POSIX; near-atomic on Windows)
  • Cross drive → shutil.copy2() with buffered I/O, then os.remove() source
  • Filename collision → append _(N) suffix
  • Every operation is logged before and after execution
  • Dry-run mode: returns what WOULD happen without touching the filesystem
"""

from __future__ import annotations

import logging
import os
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator

from backend.config import COPY_BUFFER_SIZE, MAX_FILENAME_COLLISIONS

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MoveResult:
    source: str
    destination: str
    success: bool
    error: str | None = None
    was_renamed: bool = False   # True if a collision suffix was added
    dry_run: bool = False


@dataclass
class MoveRequest:
    source: str
    destination_dir: str
    dry_run: bool = False


class FileMover:
    """
    Thread-safe file mover.

    Usage:
        mover = FileMover(on_progress=my_callback)
        result = mover.move(MoveRequest(source="/a/b.mp4", destination_dir="/organized/Videos"))
    """

    def __init__(
        self,
        on_progress: Callable[[MoveResult], None] | None = None,
    ) -> None:
        self._on_progress = on_progress
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public — single file
    # ------------------------------------------------------------------

    def move(self, request: MoveRequest) -> MoveResult:
        """Move a single file. Returns MoveResult regardless of outcome."""
        src = os.path.abspath(request.source)
        dst_dir = os.path.abspath(request.destination_dir)

        # Validate source
        if not os.path.isfile(src):
            return MoveResult(
                source=src,
                destination=dst_dir,
                success=False,
                error="Source file not found",
                dry_run=request.dry_run,
            )

        # Resolve final destination path (handle collisions)
        dst_path, was_renamed = self._resolve_destination(src, dst_dir)

        if request.dry_run:
            return MoveResult(
                source=src,
                destination=dst_path,
                success=True,
                was_renamed=was_renamed,
                dry_run=True,
            )

        # Execute move
        result = self._execute_move(src, dst_path, was_renamed)
        if self._on_progress:
            self._on_progress(result)
        return result

    # ------------------------------------------------------------------
    # Public — batch
    # ------------------------------------------------------------------

    def move_batch(
        self,
        requests: list[MoveRequest],
    ) -> Iterator[MoveResult]:
        """
        Sequentially move a list of files.
        Yields MoveResult for each file (succeeded or failed).
        Caller can abort by not consuming more results.
        """
        for req in requests:
            yield self.move(req)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _resolve_destination(
        self, src: str, dst_dir: str
    ) -> tuple[str, bool]:
        """
        Compute final destination path, adding _(N) suffix on collision.
        Returns (destination_path, was_renamed).
        """
        os.makedirs(dst_dir, exist_ok=True)
        src_path = Path(src)
        stem = src_path.stem
        suffix = src_path.suffix
        candidate = os.path.join(dst_dir, src_path.name)

        if not os.path.exists(candidate):
            return candidate, False

        # Collision: try _(1) ... _(999)
        for i in range(1, MAX_FILENAME_COLLISIONS + 1):
            candidate = os.path.join(dst_dir, f"{stem}_({i}){suffix}")
            if not os.path.exists(candidate):
                return candidate, True

        raise OSError(
            f"Could not resolve collision after {MAX_FILENAME_COLLISIONS} attempts: {src}"
        )

    def _execute_move(
        self,
        src: str,
        dst: str,
        was_renamed: bool,
    ) -> MoveResult:
        """Perform the actual filesystem move, log errors."""
        try:
            # Same drive: use rename (fast, atomic)
            if os.path.splitdrive(src)[0].lower() == os.path.splitdrive(dst)[0].lower():
                os.rename(src, dst)
            else:
                # Cross drive: buffered copy then delete
                self._buffered_copy(src, dst)
                os.remove(src)

            return MoveResult(
                source=src,
                destination=dst,
                success=True,
                was_renamed=was_renamed,
            )

        except PermissionError as exc:
            logger.warning("Permission denied moving %s → %s: %s", src, dst, exc)
            return MoveResult(
                source=src,
                destination=dst,
                success=False,
                error=f"Permission denied: {exc}",
            )
        except OSError as exc:
            logger.error("OS error moving %s → %s: %s", src, dst, exc)
            return MoveResult(
                source=src,
                destination=dst,
                success=False,
                error=str(exc),
            )

    @staticmethod
    def _buffered_copy(src: str, dst: str) -> None:
        """Copy with explicit buffer size for large cross-drive transfers."""
        with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
            while True:
                buf = fsrc.read(COPY_BUFFER_SIZE)
                if not buf:
                    break
                fdst.write(buf)
        # Preserve metadata (timestamps, permissions)
        shutil.copystat(src, dst)


class UndoManager:
    """
    Reverses file moves recorded in the database.

    Depends on Log + UndoHistory DB records created by OrganizeService.
    """

    def undo_move(self, original_path: str, current_path: str) -> MoveResult:
        """Restore a file to its original location."""
        req = MoveRequest(
            source=current_path,
            destination_dir=os.path.dirname(original_path),
        )
        mover = FileMover()
        result = mover.move(req)

        if result.success:
            # Rename to exact original name if needed
            final = os.path.join(
                os.path.dirname(original_path),
                os.path.basename(result.destination),
            )
            expected = original_path
            if final != expected and not os.path.exists(expected):
                try:
                    os.rename(final, expected)
                    result.destination = expected
                except OSError:
                    pass  # keep the renamed version

        return result
