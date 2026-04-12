"""
core/scanner.py — High-performance, multi-threaded file system scanner.

Design decisions:
  • Uses os.scandir() (3-5x faster than os.walk due to fewer stat() calls)
  • Dir traversal on worker threads; results collected via thread-safe queue
  • Bounded queue prevents memory blow-up on huge file trees
  • Incremental mode: skip files whose mtime + size match the DB record
  • Yields FileInfo dataclass objects for downstream consumers
"""

from __future__ import annotations

import logging
import os
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Generator, Iterable

from backend.config import (
    PROTECTED_PATHS,
    SCAN_CHUNK_SIZE,
    SCAN_MAX_WORKERS,
    SCAN_QUEUE_SIZE,
)
from backend.core.classifier import classify_file

logger = logging.getLogger(__name__)

# Sentinel that signals workers are done
_DONE = object()


@dataclass(slots=True)
class FileInfo:
    """Lightweight value object representing a discovered file."""

    path: str
    name: str
    extension: str
    size: int
    last_modified: float
    category: str
    is_symlink: bool = False


@dataclass
class ScanStats:
    """Mutable scan statistics updated in place by workers."""

    total_files: int = 0
    total_dirs: int = 0
    skipped_protected: int = 0
    skipped_errors: int = 0
    elapsed_seconds: float = 0.0
    files_per_second: float = 0.0


class FileScanner:
    """
    Multi-threaded recursive file scanner.

    Usage:
        scanner = FileScanner(root_paths=["/home/user", "D:\\"])
        for file_info in scanner.scan():
            process(file_info)
        print(scanner.stats)
    """

    def __init__(
        self,
        root_paths: list[str],
        *,
        max_workers: int = SCAN_MAX_WORKERS,
        exclude_patterns: list[str] | None = None,
        incremental_cache: dict[str, tuple[float, int]] | None = None,
        progress_callback: Callable[[ScanStats], None] | None = None,
    ) -> None:
        self.root_paths = [os.path.abspath(p) for p in root_paths]
        self.max_workers = max(1, max_workers)
        self.exclude_patterns = exclude_patterns or []
        self._cache = incremental_cache or {}   # path → (mtime, size)
        self._progress_cb = progress_callback
        self.stats = ScanStats()
        self._stop_event = threading.Event()
        self._dir_queue: queue.Queue[str | object] = queue.Queue(maxsize=32_768)
        self._file_queue: queue.Queue[FileInfo | object] = queue.Queue(
            maxsize=SCAN_QUEUE_SIZE
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Signal the scanner to stop at the next safe point."""
        self._stop_event.set()

    def scan(self) -> Generator[FileInfo, None, None]:
        """
        Blocking generator that yields FileInfo objects until the scan
        is complete or stop() is called.
        """
        t_start = time.monotonic()

        # Seed the directory queue with root paths
        for root in self.root_paths:
            if self._is_protected(root):
                logger.warning("Root path is protected — skipping: %s", root)
                self.stats.skipped_protected += 1
                continue
            self._dir_queue.put(root)

        # One coordinator thread drains dirs and feeds worker pool
        with ThreadPoolExecutor(
            max_workers=self.max_workers, thread_name_prefix="scanner"
        ) as pool:
            # Submit initial batch of directory-scanning tasks
            futures = set()
            active_dirs = 0

            while not self._stop_event.is_set():
                # Drain newly discovered dirs from the queue
                batch: list[str] = []
                while len(batch) < SCAN_CHUNK_SIZE:
                    try:
                        item = self._dir_queue.get_nowait()
                        if item is _DONE:
                            continue
                        batch.append(item)  # type: ignore[arg-type]
                    except queue.Empty:
                        break

                if batch:
                    active_dirs += len(batch)
                    for directory in batch:
                        fut = pool.submit(self._scan_directory, directory)
                        futures.add(fut)

                # Collect finished futures
                done_futures = {f for f in futures if f.done()}
                for fut in done_futures:
                    futures.discard(fut)
                    active_dirs -= 1
                    if exc := fut.exception():
                        logger.debug("Worker exception: %s", exc)

                # Drain file results while still waiting
                while True:
                    try:
                        fi = self._file_queue.get_nowait()
                        if fi is _DONE:
                            continue
                        self.stats.total_files += 1
                        if self._progress_cb and self.stats.total_files % 500 == 0:
                            self._progress_cb(self.stats)
                        yield fi  # type: ignore[misc]
                    except queue.Empty:
                        break

                # Exit condition: no pending work
                if active_dirs == 0 and not futures and self._dir_queue.empty():
                    break

                time.sleep(0.005)  # yield CPU briefly

        # Final drain of remaining files
        while not self._file_queue.empty():
            try:
                fi = self._file_queue.get_nowait()
                if fi is not _DONE:
                    self.stats.total_files += 1
                    yield fi  # type: ignore[misc]
            except queue.Empty:
                break

        elapsed = time.monotonic() - t_start
        self.stats.elapsed_seconds = elapsed
        self.stats.files_per_second = (
            self.stats.total_files / elapsed if elapsed > 0 else 0
        )
        logger.info(
            "Scan complete: %d files in %.2fs (%.0f files/s)",
            self.stats.total_files,
            elapsed,
            self.stats.files_per_second,
        )

    # ------------------------------------------------------------------
    # Internal worker
    # ------------------------------------------------------------------

    def _scan_directory(self, directory: str) -> None:
        """
        Scan a single directory using os.scandir().
        Subdirectories are pushed back to the shared queue.
        Files are pushed to the file queue.
        """
        if self._stop_event.is_set():
            return

        try:
            with os.scandir(directory) as it:
                for entry in it:
                    if self._stop_event.is_set():
                        return

                    try:
                        # Use cached stat where possible
                        stat = entry.stat(follow_symlinks=False)
                    except (PermissionError, OSError) as exc:
                        logger.debug("stat failed for %s: %s", entry.path, exc)
                        self.stats.skipped_errors += 1
                        continue

                    if entry.is_dir(follow_symlinks=False):
                        if not self._is_protected(entry.path):
                            self.stats.total_dirs += 1
                            self._dir_queue.put(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        fi = self._make_file_info(entry, stat)
                        if fi is not None:
                            self._file_queue.put(fi)

        except PermissionError as exc:
            logger.debug("Permission denied: %s — %s", directory, exc)
            self.stats.skipped_errors += 1
        except OSError as exc:
            logger.warning("OS error scanning %s: %s", directory, exc)
            self.stats.skipped_errors += 1

    def _make_file_info(
        self, entry: os.DirEntry, stat: os.stat_result
    ) -> FileInfo | None:
        """Build a FileInfo from a DirEntry, apply incremental cache check."""
        mtime = stat.st_mtime
        size = stat.st_size

        # Incremental scan: skip if mtime + size unchanged
        cached = self._cache.get(entry.path)
        if cached and cached == (mtime, size):
            return None

        ext = Path(entry.name).suffix.lower()
        category = classify_file(entry.name, ext)

        return FileInfo(
            path=entry.path,
            name=entry.name,
            extension=ext,
            size=size,
            last_modified=mtime,
            category=category,
            is_symlink=entry.is_symlink(),
        )

    def _is_protected(self, path: str) -> bool:
        """Return True if path is inside a system-protected directory."""
        p = os.path.abspath(path)
        for protected in PROTECTED_PATHS:
            if p == protected or p.startswith(protected + os.sep):
                self.stats.skipped_protected += 1
                return True
        return False
