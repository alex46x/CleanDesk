"""
tests/test_mover.py — Unit tests for FileMover and UndoManager.
"""

import os
from pathlib import Path

import pytest

from backend.core.mover import FileMover, MoveRequest, UndoManager


@pytest.fixture
def src_dir(tmp_path):
    """Source directory with test files."""
    d = tmp_path / "source"
    d.mkdir()
    return d


@pytest.fixture
def dst_dir(tmp_path):
    """Destination directory."""
    d = tmp_path / "dest"
    d.mkdir()
    return d


def make_file(directory: Path, name: str, content: bytes = b"data") -> Path:
    f = directory / name
    f.write_bytes(content)
    return f


class TestFileMover:

    def test_basic_move_same_drive(self, src_dir, dst_dir):
        src = make_file(src_dir, "document.pdf")
        req = MoveRequest(source=str(src), destination_dir=str(dst_dir))

        mover = FileMover()
        result = mover.move(req)

        assert result.success is True
        assert not src.exists(), "Source must be gone"
        assert (dst_dir / "document.pdf").exists(), "Destination must exist"

    def test_dry_run_does_not_move(self, src_dir, dst_dir):
        src = make_file(src_dir, "report.docx")
        req = MoveRequest(source=str(src), destination_dir=str(dst_dir), dry_run=True)

        result = FileMover().move(req)

        assert result.success is True
        assert result.dry_run is True
        assert src.exists(), "Source must still exist after dry run"
        assert not (dst_dir / "report.docx").exists(), "Destination must not be created"

    def test_missing_source_returns_failure(self, dst_dir):
        req = MoveRequest(
            source="/nonexistent/path/ghost.txt",
            destination_dir=str(dst_dir),
        )
        result = FileMover().move(req)
        assert result.success is False
        assert result.error is not None

    def test_collision_appends_suffix(self, src_dir, dst_dir):
        # Pre-create file at destination
        (dst_dir / "photo.jpg").write_bytes(b"existing")
        src = make_file(src_dir, "photo.jpg")

        result = FileMover().move(MoveRequest(str(src), str(dst_dir)))

        assert result.success is True
        assert result.was_renamed is True
        assert "(1)" in result.destination
        assert (dst_dir / "photo_(1).jpg").exists()
        assert (dst_dir / "photo.jpg").exists()   # original untouched

    def test_creates_destination_dir_if_missing(self, src_dir, tmp_path):
        src = make_file(src_dir, "x.txt")
        new_dst = tmp_path / "brand" / "new" / "folder"
        # Do not create new_dst — expect mover to do it

        result = FileMover().move(MoveRequest(str(src), str(new_dst)))

        assert result.success is True
        assert new_dst.is_dir()

    def test_progress_callback_called(self, src_dir, dst_dir):
        src = make_file(src_dir, "cb_test.txt")
        results_received = []

        def cb(r):
            results_received.append(r)

        FileMover(on_progress=cb).move(MoveRequest(str(src), str(dst_dir)))
        assert len(results_received) == 1
        assert results_received[0].success is True

    def test_batch_move(self, src_dir, dst_dir):
        files = [make_file(src_dir, f"file{i}.txt") for i in range(5)]
        requests = [MoveRequest(str(f), str(dst_dir)) for f in files]

        mover = FileMover()
        results = list(mover.move_batch(requests))

        assert len(results) == 5
        assert all(r.success for r in results)
        assert len(list(dst_dir.iterdir())) == 5


class TestUndoManager:

    def test_undo_restores_file(self, src_dir, dst_dir):
        src = make_file(src_dir, "moveme.mp4")
        original_path = str(src)

        # Move file
        mover = FileMover()
        move_result = mover.move(MoveRequest(str(src), str(dst_dir)))
        assert move_result.success

        # Undo: restore to original location
        undo_mgr = UndoManager()
        undo_result = undo_mgr.undo_move(
            original_path=original_path,
            current_path=move_result.destination,
        )

        assert undo_result.success is True
        assert Path(original_path).exists(), "File must be back at original path"
        assert not Path(move_result.destination).exists(), "New location must be empty"

    def test_undo_nonexistent_file_fails_gracefully(self, src_dir):
        undo_mgr = UndoManager()
        result = undo_mgr.undo_move(
            original_path=str(src_dir / "ghost.txt"),
            current_path="/nowhere/ghost.txt",
        )
        assert result.success is False
