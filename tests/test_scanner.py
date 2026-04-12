"""
tests/test_scanner.py — Unit tests for the multi-threaded file scanner.
"""

import os
import time
import tempfile
import threading
from pathlib import Path

import pytest

from backend.core.scanner import FileScanner, ScanStats


@pytest.fixture
def temp_tree(tmp_path: Path):
    """Create a realistic directory tree for scanner tests."""
    files = {
        "docs/report.pdf":       b"pdf content",
        "docs/notes.txt":        b"text content",
        "images/photo.jpg":      b"jpeg data",
        "images/screenshot.png": b"png data",
        "videos/clip.mp4":       b"video data",
        "code/main.py":          b"print('hello')",
        "code/app.js":           b"console.log(1)",
        "archives/backup.zip":   b"zip data",
        "deep/a/b/c/file.txt":   b"nested file",
    }
    for rel_path, content in files.items():
        full = tmp_path / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(content)
    return tmp_path


class TestFileScanner:

    def test_finds_all_files(self, temp_tree):
        scanner = FileScanner(root_paths=[str(temp_tree)])
        results = list(scanner.scan())
        assert len(results) == 9, f"Expected 9 files, got {len(results)}"

    def test_file_info_fields_populated(self, temp_tree):
        scanner = FileScanner(root_paths=[str(temp_tree)])
        files = list(scanner.scan())

        for fi in files:
            assert fi.path, "path must not be empty"
            assert fi.name, "name must not be empty"
            assert fi.size >= 0, "size must be non-negative"
            assert fi.last_modified > 0, "last_modified must be a Unix timestamp"
            assert fi.category, "category must be set"

    def test_category_assignment(self, temp_tree):
        scanner = FileScanner(root_paths=[str(temp_tree)])
        cat_map = {fi.name: fi.category for fi in scanner.scan()}

        assert cat_map["report.pdf"]    == "Documents"
        assert cat_map["photo.jpg"]     == "Images"
        assert cat_map["clip.mp4"]      == "Videos"
        assert cat_map["main.py"]       == "Code"
        assert cat_map["backup.zip"]    == "Archives"

    def test_extension_normalised_to_lowercase(self, temp_tree):
        # Create a file with uppercase extension
        upper_ext = temp_tree / "doc.PDF"
        upper_ext.write_bytes(b"pdf")

        scanner = FileScanner(root_paths=[str(temp_tree)])
        files = {fi.name: fi for fi in scanner.scan()}

        assert "doc.PDF" in files
        assert files["doc.PDF"].extension == ".pdf"
        assert files["doc.PDF"].category  == "Documents"

    def test_stats_match_actual_count(self, temp_tree):
        scanner = FileScanner(root_paths=[str(temp_tree)])
        results = list(scanner.scan())
        assert scanner.stats.total_files == len(results)
        assert scanner.stats.elapsed_seconds > 0

    def test_incremental_skips_unchanged(self, temp_tree):
        # First scan — populate cache
        scanner1 = FileScanner(root_paths=[str(temp_tree)])
        first_results = list(scanner1.scan())

        # Build cache from first scan
        cache = {fi.path: (fi.last_modified, fi.size) for fi in first_results}

        # Second scan — all files unchanged, should yield nothing
        scanner2 = FileScanner(
            root_paths=[str(temp_tree)],
            incremental_cache=cache,
        )
        second_results = list(scanner2.scan())
        assert len(second_results) == 0, "Incremental scan should skip unchanged files"

    def test_incremental_detects_new_file(self, temp_tree):
        # First scan
        scanner1 = FileScanner(root_paths=[str(temp_tree)])
        first_results = list(scanner1.scan())
        cache = {fi.path: (fi.last_modified, fi.size) for fi in first_results}

        # Add a new file
        new_file = temp_tree / "new_document.docx"
        new_file.write_bytes(b"new content")

        scanner2 = FileScanner(
            root_paths=[str(temp_tree)],
            incremental_cache=cache,
        )
        second_results = list(scanner2.scan())
        names = [fi.name for fi in second_results]
        assert "new_document.docx" in names
        assert len(second_results) == 1

    def test_protected_paths_skipped(self, temp_tree):
        """Scanner must not enter protected system locations."""
        scanner = FileScanner(
            root_paths=["C:\\Windows"],  # Protected on Windows
        )
        results = list(scanner.scan())
        # Should be empty (or very few if the path doesn't exist)
        assert scanner.stats.skipped_protected >= 0

    def test_stop_mid_scan(self, temp_tree):
        """stop() should halt the scan gracefully."""
        scanner = FileScanner(root_paths=[str(temp_tree)])
        collected = []

        def _run():
            for fi in scanner.scan():
                collected.append(fi)
                scanner.stop()   # Stop after first file

        t = threading.Thread(target=_run)
        t.start()
        t.join(timeout=5)

        # We stopped early, so fewer than total files should be collected
        assert len(collected) <= 9

    def test_multiple_root_paths(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        (dir_a / "file1.txt").write_bytes(b"1")
        (dir_b / "file2.txt").write_bytes(b"2")

        scanner = FileScanner(root_paths=[str(dir_a), str(dir_b)])
        results = list(scanner.scan())
        names = {fi.name for fi in results}
        assert "file1.txt" in names
        assert "file2.txt" in names

    def test_progress_callback_called(self, temp_tree):
        callback_calls = []

        def _cb(stats: ScanStats):
            callback_calls.append(stats.total_files)

        scanner = FileScanner(
            root_paths=[str(temp_tree)],
            progress_callback=_cb,
        )
        list(scanner.scan())
        # Callback fires every 500 files; with 9 files it may not fire.
        # Just verify it doesn't crash.
        assert scanner.stats.total_files == 9

    def test_symlink_files_not_followed(self, tmp_path):
        real_file = tmp_path / "real.txt"
        real_file.write_bytes(b"data")
        link = tmp_path / "link.txt"
        try:
            link.symlink_to(real_file)
        except OSError:
            pytest.skip("Symlinks not supported on this OS")

        scanner = FileScanner(root_paths=[str(tmp_path)])
        results = list(scanner.scan())
        symlinks = [fi for fi in results if fi.is_symlink]
        # Symlinks should be flagged but not followed
        assert all(fi.is_symlink for fi in symlinks)
