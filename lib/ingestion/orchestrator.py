"""Orchestrate: fetched bytes -> parsed text -> LLM summary -> papers/<id>/."""
from __future__ import annotations

import datetime as dt
import tempfile
from pathlib import Path

from lib.ingestion.fetchers.upload import FetchedSource
from lib.ingestion.pdf_parser import parse_pdf
from lib.ingestion.summarize import summarize_paper
from lib.llm.base import LLMClient
from lib.models import IngestResult, PaperMeta
from lib.storage import PaperStorage, allocate_paper_id, content_hash


def _utcnow_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ingest_pdf(
    *,
    fetched: FetchedSource,
    storage: PaperStorage,
    seed_taxonomy: list[str],
    llm: LLMClient,
    max_full_md_chars: int,
) -> IngestResult:
    h = content_hash(fetched.raw_bytes)
    existing = storage.find_by_hash(h)
    if existing is not None:
        return IngestResult(paper_id=existing, created=False,
                            message=f"already ingested as {existing}")

    # write PDF to a temp file for PyMuPDF (it wants a path)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(fetched.raw_bytes)
        tmp_path = Path(tmp.name)
    try:
        parsed = parse_pdf(tmp_path, max_chars=max_full_md_chars)
    finally:
        tmp_path.unlink(missing_ok=True)

    summary = summarize_paper(
        full_md=parsed.text, seed_taxonomy=seed_taxonomy, llm=llm,
    )

    paper_id = allocate_paper_id(
        storage, year=summary.year, slug_hint=summary.title,
    )
    pdir = storage.paper_dir(paper_id)
    pdir.mkdir(parents=True, exist_ok=False)
    (pdir / "source.pdf").write_bytes(fetched.raw_bytes)
    (pdir / "full.md").write_text(parsed.text)
    (pdir / "notes.md").write_text(summary.notes_md)

    meta = PaperMeta(
        paper_id=paper_id,
        title=summary.title,
        authors=summary.authors,
        year=summary.year,
        arxiv_id=fetched.arxiv_id,
        url=fetched.url,
        keywords=summary.keywords,
        primary_category=summary.primary_category,
        secondary_categories=summary.secondary_categories,
        ingested_at=_utcnow_iso(),
        source_type=fetched.source_type,  # type: ignore[arg-type]
        content_hash=h,
        one_line_summary=summary.one_line_summary,
        notes_status="ok",
        full_md_truncated=parsed.truncated,
    )
    storage.write_meta(meta)
    return IngestResult(paper_id=paper_id, created=True,
                        message=f"ingested {paper_id}")
