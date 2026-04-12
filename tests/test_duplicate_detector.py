"""
tests/test_duplicate_detector.py — Unit tests for DuplicateDetector.
"""

import os
from pathlib import Path

import pytest

from backend.core.duplicate_detector import DuplicateDetector


@pytest.fixture
def dupes_tree(tmp_path: Path):
    """
    Creates:
      - 3 files with identical content (1 group of 3)
      - 2 files with different identical content (1 group of 2)
      - 1 unique file
    """
    # Group 1: same content → 2 extras wasted
    content_a = b"duplicate content A" * 200   # > 1 KB
    for name in ["a1.txt", "a2.txt", "a3.txt"]:
        (tmp_path / name).write_bytes(content_a)

    # Group 2: same content → 1 extra wasted
    content_b = b"duplicate content B" * 150
    for name in ["b1.pdf", "b2.pdf"]:
        (tmp_path / name).write_bytes(content_b)

    # Unique
    (tmp_path / "unique.mp4").write_bytes(b"completely unique" * 100)

    return tmp_path


class TestDuplicateDetector:

    def _file_pairs(self, directory: Path):
        return [
            (str(f), f.stat().st_size)
            for f in directory.iterdir()
            if f.is_file()
        ]

    def test_finds_two_groups(self, dupes_tree):
        detector = DuplicateDetector(max_workers=2)
        pairs = self._file_pairs(dupes_tree)
        groups = detector.find_duplicates(pairs)

        assert len(groups) == 2, f"Expected 2 groups, got {len(groups)}"

    def test_group_sizes_correct(self, dupes_tree):
        detector = DuplicateDetector()
        pairs = self._file_pairs(dupes_tree)
        groups = detector.find_duplicates(pairs)

        file_counts = sorted([len(g.files) for g in groups], reverse=True)
        assert file_counts == [3, 2], f"Got {file_counts}"

    def test_wasted_bytes_calculated(self, dupes_tree):
        detector = DuplicateDetector()
        pairs = self._file_pairs(dupes_tree)
        groups = detector.find_duplicates(pairs)

        for g in groups:
            expected_wasted = g.size * (len(g.files) - 1)
            assert g.wasted_bytes == expected_wasted

    def test_sorted_by_wasted_space(self, dupes_tree):
        detector = DuplicateDetector()
        pairs = self._file_pairs(dupes_tree)
        groups = detector.find_duplicates(pairs)

        # Largest wasted first
        for i in range(len(groups) - 1):
            assert groups[i].wasted_bytes >= groups[i + 1].wasted_bytes

    def test_unique_file_not_in_any_group(self, dupes_tree):
        detector = DuplicateDetector()
        pairs = self._file_pairs(dupes_tree)
        groups = detector.find_duplicates(pairs)

        all_paths = {p for g in groups for p in g.files}
        unique_path = str(dupes_tree / "unique.mp4")
        assert unique_path not in all_paths, "Unique file should not be in any group"

    def test_empty_input(self):
        detector = DuplicateDetector()
        groups = detector.find_duplicates([])
        assert groups == []

    def test_all_unique_files(self, tmp_path):
        for i in range(5):
            (tmp_path / f"unique_{i}.bin").write_bytes(
                b"unique content " + str(i).encode() * 200
            )
        pairs = [(str(f), f.stat().st_size) for f in tmp_path.iterdir()]
        groups = DuplicateDetector().find_duplicates(pairs)
        assert len(groups) == 0

    def test_small_files_below_threshold_skipped(self, tmp_path):
        # Files < HASH_MIN_SIZE (1024 bytes) should be ignored
        for i in range(3):
            (tmp_path / f"tiny_{i}.txt").write_bytes(b"tiny")  # 4 bytes

        pairs = [(str(f), f.stat().st_size) for f in tmp_path.iterdir()]
        groups = DuplicateDetector().find_duplicates(pairs)
        assert len(groups) == 0, "Tiny files should be excluded from detection"

    def test_progress_callback_fires(self, dupes_tree):
        calls = []

        def cb(done, total):
            calls.append((done, total))

        detector = DuplicateDetector(progress_callback=cb)
        pairs = self._file_pairs(dupes_tree)
        detector.find_duplicates(pairs)

        assert len(calls) > 0, "Progress callback was never called"
        # Last call: done == total
        last_done, last_total = calls[-1]
        assert last_done == last_total
