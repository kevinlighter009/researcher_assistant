"""Typed domain models. PaperMeta corresponds to papers/<id>/meta.json."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


NotesStatus = Literal["ok", "pending", "failed"]
SourceType = Literal["upload", "arxiv", "web", "search"]


class PaperMeta(BaseModel):
    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int
    arxiv_id: Optional[str] = None
    url: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    primary_category: str
    secondary_categories: list[str] = Field(default_factory=list)
    ingested_at: str  # ISO 8601 UTC
    source_type: SourceType
    content_hash: str
    one_line_summary: str
    notes_status: NotesStatus = "pending"
    full_md_truncated: bool = False


class IngestResult(BaseModel):
    paper_id: str
    created: bool   # False if already existed
    message: str
