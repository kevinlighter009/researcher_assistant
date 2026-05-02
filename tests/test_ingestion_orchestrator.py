import json
from pathlib import Path

import fitz
import pytest

from lib.ingestion.orchestrator import ingest_pdf
from lib.ingestion.fetchers.upload import FetchedSource
from lib.llm.fake import FakeLLMClient
from lib.storage import PaperStorage


def make_pdf(path: Path, text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()
    return path.read_bytes()


SUMMARY_JSON = json.dumps({
    "title": "Sample VLA Paper",
    "authors": ["Alice"],
    "year": 2025,
    "primary_category": "vla",
    "secondary_categories": [],
    "keywords": ["vla", "driving"],
    "one_line_summary": "VLA for driving.",
    "notes_md": "## Method\nA VLA.\n",
})


def make_fetched(tmp_path: Path) -> FetchedSource:
    pdf = tmp_path / "Sample VLA Paper.pdf"
    raw = make_pdf(pdf, "Hello VLA")
    return FetchedSource(
        raw_bytes=raw,
        suggested_title="Sample VLA Paper",
        source_type="upload",
    )


def test_ingest_pdf_creates_paper(tmp_path):
    storage = PaperStorage(tmp_path)
    fetched = make_fetched(tmp_path)
    fake = FakeLLMClient(responses=[SUMMARY_JSON])
    result = ingest_pdf(
        fetched=fetched, storage=storage,
        seed_taxonomy=["vla", "misc"], llm=fake, max_full_md_chars=10000,
    )
    assert result.created is True
    assert result.paper_id.startswith("2025-")
    pdir = storage.paper_dir(result.paper_id)
    assert (pdir / "source.pdf").exists()
    assert (pdir / "full.md").exists()
    assert (pdir / "notes.md").read_text().startswith("## Method")
    meta = storage.read_meta(result.paper_id)
    assert meta.title == "Sample VLA Paper"
    assert meta.primary_category == "vla"
    assert meta.notes_status == "ok"
    assert meta.source_type == "upload"


def test_ingest_pdf_is_idempotent_on_hash(tmp_path):
    storage = PaperStorage(tmp_path)
    fetched = make_fetched(tmp_path)
    fake1 = FakeLLMClient(responses=[SUMMARY_JSON])
    r1 = ingest_pdf(fetched=fetched, storage=storage,
                    seed_taxonomy=["vla", "misc"], llm=fake1,
                    max_full_md_chars=10000)
    fake2 = FakeLLMClient(responses=[SUMMARY_JSON])  # would be a 2nd call
    r2 = ingest_pdf(fetched=fetched, storage=storage,
                    seed_taxonomy=["vla", "misc"], llm=fake2,
                    max_full_md_chars=10000)
    assert r1.paper_id == r2.paper_id
    assert r2.created is False
    assert len(fake2.calls) == 0  # short-circuited before LLM


def test_ingest_pdf_marks_truncation(tmp_path):
    storage = PaperStorage(tmp_path)
    fetched = make_fetched(tmp_path)
    fake = FakeLLMClient(responses=[SUMMARY_JSON])
    result = ingest_pdf(
        fetched=fetched, storage=storage,
        seed_taxonomy=["vla", "misc"], llm=fake,
        max_full_md_chars=5,  # forces truncation
    )
    meta = storage.read_meta(result.paper_id)
    assert meta.full_md_truncated is True
