"""Tests for lib.notes.store."""
from __future__ import annotations

from pathlib import Path

import pytest

from lib.notes.store import (
    NoteStatus,
    note_path_for,
    read_note,
    write_note,
)


def test_note_path_mirrors_source_relpath(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    src = repo_root / "doc" / "distilled" / "vla" / "drivevlm-2024.md"
    src.parent.mkdir(parents=True)
    src.write_text("source")
    notes_root = repo_root / "doc" / "notes"
    np = note_path_for(src, repo_root=repo_root, notes_root=notes_root)
    assert np == notes_root / "doc" / "distilled" / "vla" / "drivevlm-2024.md"


def test_note_path_for_top_level_source(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    src = repo_root / "README.md"
    src.write_text("hi")
    notes_root = repo_root / "doc" / "notes"
    np = note_path_for(src, repo_root=repo_root, notes_root=notes_root)
    assert np == notes_root / "README.md"


def test_note_path_rejects_source_outside_repo(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    other = tmp_path / "elsewhere.md"
    other.write_text("x")
    with pytest.raises(ValueError, match="not inside repo_root"):
        note_path_for(
            other, repo_root=repo_root, notes_root=repo_root / "doc" / "notes",
        )


def test_read_note_when_missing(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    src = repo_root / "a.md"
    src.write_text("source")
    text, status = read_note(
        src, repo_root=repo_root, notes_root=repo_root / "notes",
    )
    assert text == ""
    assert isinstance(status, NoteStatus)
    assert status.exists is False
    assert status.last_modified is None


def test_write_then_read_round_trip(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    src = repo_root / "doc" / "distilled" / "vla" / "x.md"
    src.parent.mkdir(parents=True)
    src.write_text("source")
    notes_root = repo_root / "notes"
    status = write_note(
        src, "my thoughts on this paper",
        repo_root=repo_root, notes_root=notes_root,
    )
    assert status.exists
    assert status.size_chars == len("my thoughts on this paper")
    assert status.last_modified  # non-empty ISO string

    text, status2 = read_note(
        src, repo_root=repo_root, notes_root=notes_root,
    )
    assert text == "my thoughts on this paper"
    assert status2.exists
    # Path matches
    assert status2.path == status.path
    # File on disk
    assert status.path.exists()
    assert "my thoughts" in status.path.read_text()


def test_write_creates_parent_dirs(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    src = repo_root / "deep" / "nested" / "path" / "file.md"
    src.parent.mkdir(parents=True)
    src.write_text("source")
    notes_root = repo_root / "notes"
    status = write_note(
        src, "content", repo_root=repo_root, notes_root=notes_root,
    )
    assert status.path.exists()
    assert (notes_root / "deep" / "nested" / "path").is_dir()


def test_empty_content_deletes_existing_note(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    src = repo_root / "x.md"
    src.write_text("source")
    notes_root = repo_root / "notes"
    write_note(src, "first version", repo_root=repo_root, notes_root=notes_root)
    np = note_path_for(src, repo_root=repo_root, notes_root=notes_root)
    assert np.exists()
    # Now save empty content
    status = write_note(
        src, "   \n\n", repo_root=repo_root, notes_root=notes_root,
    )
    assert not status.exists
    assert not np.exists()


def test_empty_content_when_no_note_is_noop(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    src = repo_root / "x.md"
    src.write_text("source")
    notes_root = repo_root / "notes"
    status = write_note(
        src, "", repo_root=repo_root, notes_root=notes_root,
    )
    assert not status.exists
    # No file was created, no parents either
    assert not status.path.exists()
