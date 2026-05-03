"""Simple file-backed notes store for the Wiki Browser.

A note is a Markdown file mirroring the source file's path under
``<notes_root>/`` (default ``doc/notes/``). For example, a note attached
to ``doc/distilled/vla/drivevlm-2024.md`` lives at
``doc/notes/doc/distilled/vla/drivevlm-2024.md``. Mirror layout means notes
are easy to browse alongside the corpus they annotate, and easy to commit.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class NoteStatus:
    """Metadata about a note file."""

    path: Path
    exists: bool
    last_modified: Optional[str] = None    # ISO 8601 UTC, second precision
    size_chars: int = 0


def note_path_for(
    source_path: Path,
    *,
    repo_root: Path,
    notes_root: Path,
) -> Path:
    """Return the canonical notes file path for ``source_path``.

    The note's relative path under ``notes_root`` mirrors ``source_path``'s
    relative path under ``repo_root``. ``source_path`` MUST be inside
    ``repo_root`` (after resolving). Raises ``ValueError`` otherwise.
    """
    source_path = Path(source_path).resolve()
    repo_root = Path(repo_root).resolve()
    notes_root = Path(notes_root)
    try:
        rel = source_path.relative_to(repo_root)
    except ValueError as e:
        raise ValueError(
            f"source_path {source_path} is not inside repo_root {repo_root}"
        ) from e
    return notes_root / rel


def read_note(
    source_path: Path,
    *,
    repo_root: Path,
    notes_root: Path,
) -> tuple[str, NoteStatus]:
    """Return ``(content, NoteStatus)`` for the note attached to
    ``source_path``. If the note doesn't exist yet, content is the empty
    string and ``status.exists`` is False.
    """
    np = note_path_for(source_path, repo_root=repo_root, notes_root=notes_root)
    if not np.exists():
        return "", NoteStatus(path=np, exists=False)
    text = np.read_text()
    mtime = dt.datetime.fromtimestamp(
        np.stat().st_mtime, tz=dt.timezone.utc,
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    return text, NoteStatus(
        path=np, exists=True, last_modified=mtime, size_chars=len(text),
    )


def write_note(
    source_path: Path,
    content: str,
    *,
    repo_root: Path,
    notes_root: Path,
) -> NoteStatus:
    """Write ``content`` to the note for ``source_path`` (creating parent
    directories as needed). If ``content`` is empty/whitespace and the
    note already exists, it is **deleted** (so an empty note doesn't leave
    a stub file). Returns the post-write status.
    """
    np = note_path_for(source_path, repo_root=repo_root, notes_root=notes_root)
    if not content.strip():
        if np.exists():
            np.unlink()
        return NoteStatus(path=np, exists=False)
    np.parent.mkdir(parents=True, exist_ok=True)
    # Atomic-ish write
    tmp = np.with_suffix(np.suffix + ".tmp")
    tmp.write_text(content)
    tmp.replace(np)
    mtime = dt.datetime.fromtimestamp(
        np.stat().st_mtime, tz=dt.timezone.utc,
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    return NoteStatus(
        path=np, exists=True, last_modified=mtime, size_chars=len(content),
    )
