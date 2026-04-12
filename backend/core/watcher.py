"""
core/watcher.py — Real-time file system monitoring using Watchdog.

Behaviour:
  • Monitors one or more root directories recursively
  • Debounces rapid event bursts (e.g., app saving temp files)
  • Emits FileEvent objects to registered handlers
  • Thread-safe, can be started/stopped cleanly
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from watchdog.events import (
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from backend.config import WATCHER_DEBOUNCE_SECONDS

logger = logging.getLogger(__name__)


class EventKind(str, Enum):
    CREATED = "created"
    DELETED = "deleted"
    MODIFIED = "modified"
    MOVED = "moved"


@dataclass(slots=True)
class FileEvent:
    kind: EventKind
    src_path: str
    dest_path: str | None = None      # Only for MOVED events


EventHandler = Callable[[FileEvent], None]


class _DebounceHandler(FileSystemEventHandler):
    """Watchdog event handler with debouncing."""

    def __init__(
        self,
        callback: EventHandler,
        debounce_seconds: float,
    ) -> None:
        super().__init__()
        self._callback = callback
        self._debounce = debounce_seconds
        self._pending: dict[str, tuple[EventKind, str | None, float]] = {}
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    # ---- Watchdog overrides ----

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._queue(EventKind.CREATED, event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._queue(EventKind.DELETED, event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._queue(EventKind.MODIFIED, event.src_path)

    def on_moved(self, event: FileMovedEvent) -> None:
        if not event.is_directory:
            self._queue(EventKind.MOVED, event.src_path, event.dest_path)

    # ---- Internal ----

    def _queue(self, kind: EventKind, src: str, dest: str | None = None) -> None:
        with self._lock:
            self._pending[src] = (kind, dest, time.monotonic())
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(
                self._debounce, self._flush
            )
            self._timer.daemon = True
            self._timer.start()

    def _flush(self) -> None:
        with self._lock:
            events = list(self._pending.values())
            self._pending.clear()

        for kind, dest, _ in events:
            # Re-derive src from pending dict key — rebuild from stored tuple
            pass

        # Cleaner approach: flush all distinct events we have
        # (already deduplicated by path)
        with self._lock:
            pending_copy = dict(self._pending)

        for src, (kind, dest, _) in pending_copy.items():
            try:
                self._callback(FileEvent(kind=kind, src_path=src, dest_path=dest))
            except Exception as exc:
                logger.error("Watcher callback error: %s", exc)


class FileWatcher:
    """
    Manages one Watchdog Observer watching multiple directories.

    Usage:
        watcher = FileWatcher(handler=my_handler)
        watcher.add_path("/home/user/Downloads")
        watcher.start()
        # ... later ...
        watcher.stop()
    """

    def __init__(
        self,
        handler: EventHandler,
        debounce_seconds: float = WATCHER_DEBOUNCE_SECONDS,
    ) -> None:
        self._handler = handler
        self._debounce = debounce_seconds
        self._observer: Observer | None = None
        self._watched_paths: list[str] = []
        self._running = False

    def add_path(self, path: str) -> None:
        """Add a path to watch. Can be called before or after start()."""
        if path not in self._watched_paths:
            self._watched_paths.append(path)
            if self._observer and self._running:
                self._schedule(path)

    def remove_path(self, path: str) -> None:
        if path in self._watched_paths:
            self._watched_paths.remove(path)

    def start(self) -> None:
        if self._running:
            return

        self._observer = Observer()
        event_handler = _DebounceHandler(self._handler, self._debounce)

        for path in self._watched_paths:
            self._schedule(path, event_handler)

        self._observer.start()
        self._running = True
        logger.info(
            "FileWatcher started on %d path(s): %s",
            len(self._watched_paths),
            self._watched_paths,
        )

    def stop(self) -> None:
        if self._observer and self._running:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._running = False
            logger.info("FileWatcher stopped")

    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    def _schedule(
        self,
        path: str,
        handler: _DebounceHandler | None = None,
    ) -> None:
        if handler is None:
            handler = _DebounceHandler(self._handler, self._debounce)
        try:
            self._observer.schedule(handler, path=path, recursive=True)  # type: ignore[union-attr]
        except FileNotFoundError:
            logger.warning("Watch path not found, skipping: %s", path)
        except Exception as exc:
            logger.error("Failed to schedule watch on %s: %s", path, exc)
