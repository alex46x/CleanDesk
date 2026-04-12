"""
core/duplicate_detector.py — Hash-based duplicate file detector.

Algorithm (optimised for large datasets):
  Stage 1: Group files by size — O(n), zero I/O
  Stage 2: Within same-size groups, compare first-block hash (partial read)
  Stage 3: Full-file XXHash64 for confirmed duplicates

XXHash64 is used instead of MD5/SHA because it is ~10x faster and
sufficient for deduplication (not security-critical).

Falls back gracefully if xxhash is not installed (uses SHA-256 instead).
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable

from backend.config import HASH_CHUNK_SIZE, HASH_MIN_SIZE, SCAN_MAX_WORKERS

logger = logging.getLogger(__name__)

try:
    import xxhash  # type: ignore[import]
    _HAS_XXHASH = True
except ImportError:
    _HAS_XXHASH = False
    logger.warning("xxhash not installed — using SHA-256 (slower). Install: pip install xxhash")


@dataclass
class DuplicateGroup:
    """One set of identical files."""

    fingerprint: str
    size: int
    files: list[str] = field(default_factory=list)

    @property
    def wasted_bytes(self) -> int:
        return self.size * (len(self.files) - 1)


class DuplicateDetector:
    """
    Detects duplicate files from a list of (path, size) tuples.

    Usage:
        detector = DuplicateDetector()
        groups = detector.find_duplicates([(path, size), ...])
    """

    def __init__(
        self,
        max_workers: int = SCAN_MAX_WORKERS,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        self.max_workers = max(1, max_workers)
        self._progress_cb = progress_callback
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def find_duplicates(
        self, files: list[tuple[str, int]]
    ) -> list[DuplicateGroup]:
        """
        files: list of (absolute_path, file_size_bytes)
        Returns DuplicateGroup list, sorted by wasted space descending.
        """
        if not files:
            return []

        logger.info("Duplicate detection starting on %d files", len(files))

        # Stage 1: group by size
        by_size: dict[int, list[str]] = defaultdict(list)
        for path, size in files:
            if size >= HASH_MIN_SIZE:
                by_size[size].append(path)

        candidates = [
            paths for paths in by_size.values() if len(paths) > 1
        ]
        logger.debug(
            "Stage 1: %d size groups with potential duplicates", len(candidates)
        )

        if not candidates:
            return []

        # Stage 2: partial hash (first 64 KB) to quickly discard non-twins
        by_partial: dict[str, list[str]] = defaultdict(list)
        all_paths = [p for group in candidates for p in group]

        partial_hashes = self._hash_files_parallel(
            all_paths, partial=True, label="partial"
        )
        for path, h in partial_hashes.items():
            by_partial[h].append(path)

        stage2_candidates = {
            h: paths for h, paths in by_partial.items() if len(paths) > 1
        }
        logger.debug(
            "Stage 2: %d partial-hash groups", len(stage2_candidates)
        )

        # Stage 3: full hash to confirm
        stage3_paths = [
            p for paths in stage2_candidates.values() for p in paths
        ]
        full_hashes = self._hash_files_parallel(
            stage3_paths, partial=False, label="full"
        )

        by_full: dict[str, list[str]] = defaultdict(list)
        for path, h in full_hashes.items():
            by_full[h].append(path)

        # Build result groups
        groups: list[DuplicateGroup] = []
        for h, paths in by_full.items():
            if len(paths) > 1:
                # Determine size from our input map
                size_map = dict(files)
                size = size_map.get(paths[0], 0)
                groups.append(DuplicateGroup(fingerprint=h, size=size, files=paths))

        groups.sort(key=lambda g: g.wasted_bytes, reverse=True)
        total_wasted = sum(g.wasted_bytes for g in groups)
        logger.info(
            "Found %d duplicate groups, %.2f MB wasted",
            len(groups),
            total_wasted / 1_048_576,
        )
        return groups

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _hash_files_parallel(
        self,
        paths: list[str],
        *,
        partial: bool,
        label: str,
    ) -> dict[str, str]:
        """Hash a list of files in parallel. Returns path → hash dict."""
        results: dict[str, str] = {}
        completed = 0
        total = len(paths)

        with ThreadPoolExecutor(
            max_workers=self.max_workers, thread_name_prefix=f"hasher_{label}"
        ) as pool:
            future_to_path = {
                pool.submit(self._hash_file, p, partial): p for p in paths
            }
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                completed += 1
                if self._progress_cb:
                    self._progress_cb(completed, total)
                try:
                    h = future.result()
                    if h:
                        results[path] = h
                except Exception as exc:
                    logger.debug("Hash error for %s: %s", path, exc)

        return results

    def _hash_file(self, path: str, partial: bool) -> str | None:
        """Return hex digest for a file. partial=True reads first 64 KB only."""
        read_limit = 65_536 if partial else None  # 64 KB partial read

        try:
            if _HAS_XXHASH:
                hasher = xxhash.xxh64()
            else:
                hasher = hashlib.sha256()

            with open(path, "rb") as f:
                if read_limit:
                    chunk = f.read(read_limit)
                    if chunk:
                        hasher.update(chunk)
                else:
                    while True:
                        chunk = f.read(HASH_CHUNK_SIZE)
                        if not chunk:
                            break
                        hasher.update(chunk)

            return hasher.hexdigest()

        except (PermissionError, FileNotFoundError, OSError) as exc:
            logger.debug("Cannot hash %s: %s", path, exc)
            return None
