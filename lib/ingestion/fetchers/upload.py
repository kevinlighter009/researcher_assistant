"""Fetcher for local PDF files supplied by the user."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FetchedSource:
    raw_bytes: bytes
    suggested_title: str
    source_type: str          # "upload" | "arxiv" | "web" | "search"
    url: Optional[str] = None
    arxiv_id: Optional[str] = None


def upload_fetch(path: Path) -> FetchedSource:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"upload_fetch must be a PDF, got {path.suffix}")
    return FetchedSource(
        raw_bytes=path.read_bytes(),
        suggested_title=path.stem,
        source_type="upload",
    )
