import json
import pytest
from pydantic import ValidationError

from lib.models import PaperMeta, IngestResult


def test_paper_meta_round_trip():
    m = PaperMeta(
        paper_id="2024-2406.12345",
        title="A Driving World Model",
        authors=["Alice", "Bob"],
        year=2024,
        arxiv_id="2406.12345",
        url=None,
        keywords=["world model", "diffusion"],
        primary_category="world_model",
        secondary_categories=["diffusion_decoder"],
        ingested_at="2026-05-02T10:00:00Z",
        source_type="upload",
        content_hash="deadbeef",
        one_line_summary="A diffusion world model for driving.",
        notes_status="ok",
    )
    j = m.model_dump_json()
    m2 = PaperMeta.model_validate_json(j)
    assert m2 == m


def test_paper_meta_requires_paper_id():
    with pytest.raises(ValidationError):
        PaperMeta(title="x", authors=[], year=2024,
                  primary_category="misc",
                  ingested_at="t", source_type="upload",
                  content_hash="h", one_line_summary="s",
                  notes_status="ok")


def test_paper_meta_notes_status_enum():
    with pytest.raises(ValidationError):
        PaperMeta(
            paper_id="x", title="x", authors=[], year=2024,
            primary_category="misc", ingested_at="t",
            source_type="upload", content_hash="h",
            one_line_summary="s", notes_status="bogus",
        )


def test_ingest_result_shape():
    r = IngestResult(paper_id="x", created=True, message="ok")
    assert r.created is True
