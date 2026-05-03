import json
from pathlib import Path

import fitz

from lib.pipeline import ingest_pdf_and_index
from lib.indexing.writer import WikiPaths
from lib.ingestion.fetchers.upload import FetchedSource
from lib.llm.fake import FakeLLMClient
from lib.storage import PaperStorage


def make_pdf_bytes(tmp_path: Path) -> bytes:
    p = tmp_path / "p.pdf"
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "hello")
    doc.save(str(p))
    doc.close()
    return p.read_bytes()


SUMMARY = json.dumps({
    "title": "T", "authors": [], "year": 2024,
    "primary_category": "vla", "secondary_categories": [],
    "keywords": ["k"], "one_line_summary": "s",
    "notes_md": "n",
})


def test_pipeline_ingests_and_indexes(tmp_path):
    storage = PaperStorage(tmp_path)
    paths = WikiPaths(tmp_path / "wiki")
    fetched = FetchedSource(
        raw_bytes=make_pdf_bytes(tmp_path),
        suggested_title="T", source_type="upload",
    )
    fake = FakeLLMClient(responses=[SUMMARY])
    result = ingest_pdf_and_index(
        fetched=fetched, storage=storage, wiki_paths=paths,
        seed_taxonomy=["vla", "misc"], llm=fake, max_full_md_chars=10000,
    )
    assert result.created is True
    assert "| 2024-t |" in paths.index_md.read_text()
    assert "2024-t" in paths.category_md("vla").read_text()


def test_pipeline_skips_index_on_duplicate(tmp_path):
    storage = PaperStorage(tmp_path)
    paths = WikiPaths(tmp_path / "wiki")
    fetched = FetchedSource(
        raw_bytes=make_pdf_bytes(tmp_path),
        suggested_title="T", source_type="upload",
    )
    fake = FakeLLMClient(responses=[SUMMARY])
    ingest_pdf_and_index(
        fetched=fetched, storage=storage, wiki_paths=paths,
        seed_taxonomy=["vla", "misc"], llm=fake, max_full_md_chars=10000,
    )
    before = paths.index_md.read_text()
    fake2 = FakeLLMClient(responses=[SUMMARY])
    r2 = ingest_pdf_and_index(
        fetched=fetched, storage=storage, wiki_paths=paths,
        seed_taxonomy=["vla", "misc"], llm=fake2, max_full_md_chars=10000,
    )
    after = paths.index_md.read_text()
    assert r2.created is False
    assert before == after
    assert len(fake2.calls) == 0
