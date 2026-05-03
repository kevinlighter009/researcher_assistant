from pathlib import Path

import pytest

from lib.indexing.writer import upsert_paper_in_wiki, WikiPaths
from lib.models import PaperMeta


def make_meta(pid="2024-x", year=2024, cat="vla", summary="s",
              keywords=("k1", "k2"), title="A Title") -> PaperMeta:
    return PaperMeta(
        paper_id=pid, title=title, authors=[], year=year,
        primary_category=cat, ingested_at="2026-05-02T00:00:00Z",
        source_type="upload", content_hash="h",
        keywords=list(keywords),
        one_line_summary=summary, notes_status="ok",
    )


def test_creates_index_and_category_file(tmp_path):
    paths = WikiPaths(tmp_path / "wiki")
    upsert_paper_in_wiki(make_meta(), paths)
    idx = (tmp_path / "wiki" / "index.md").read_text()
    cat = (tmp_path / "wiki" / "categories" / "vla.md").read_text()
    assert "| paper_id |" in idx  # header present
    assert "| 2024-x | 2024 | A Title | vla | s | k1, k2 |" in idx
    assert "# vla" in cat
    assert "2024-x" in cat


def test_idempotent_upsert(tmp_path):
    paths = WikiPaths(tmp_path / "wiki")
    upsert_paper_in_wiki(make_meta(), paths)
    upsert_paper_in_wiki(make_meta(summary="updated"), paths)
    idx = (tmp_path / "wiki" / "index.md").read_text()
    # only one row for 2024-x
    assert idx.count("| 2024-x |") == 1
    assert "updated" in idx
    assert "| s |" not in idx


def test_two_papers_same_category(tmp_path):
    paths = WikiPaths(tmp_path / "wiki")
    upsert_paper_in_wiki(make_meta(pid="2024-a"), paths)
    upsert_paper_in_wiki(make_meta(pid="2024-b"), paths)
    cat = (tmp_path / "wiki" / "categories" / "vla.md").read_text()
    assert "2024-a" in cat
    assert "2024-b" in cat


def test_recategorize_removes_from_old_category(tmp_path):
    paths = WikiPaths(tmp_path / "wiki")
    upsert_paper_in_wiki(make_meta(pid="2024-x", cat="vla"), paths)
    upsert_paper_in_wiki(make_meta(pid="2024-x", cat="world_model"), paths)
    vla = (tmp_path / "wiki" / "categories" / "vla.md").read_text()
    wm = (tmp_path / "wiki" / "categories" / "world_model.md").read_text()
    assert "2024-x" not in vla
    assert "2024-x" in wm
