import json
from pathlib import Path

import pytest

from lib.storage import (
    PaperStorage, content_hash, allocate_paper_id, slugify,
)
from lib.models import PaperMeta


def make_meta(paper_id: str, year: int = 2024, hash_: str = "abc") -> PaperMeta:
    return PaperMeta(
        paper_id=paper_id, title="t", authors=[], year=year,
        primary_category="misc", ingested_at="2026-05-02T00:00:00Z",
        source_type="upload", content_hash=hash_,
        one_line_summary="s", notes_status="pending",
    )


def test_content_hash_stable():
    assert content_hash(b"abc") == content_hash(b"abc")
    assert content_hash(b"abc") != content_hash(b"abd")


def test_slugify():
    assert slugify("Hello, World! 2024") == "hello-world-2024"
    assert slugify("  a   b  ") == "a-b"
    assert slugify("π—λ") == "unknown"  # non-ascii fallback


def test_allocate_paper_id_unique(tmp_path):
    storage = PaperStorage(tmp_path)
    a = allocate_paper_id(storage, year=2024, slug_hint="vla-paper")
    storage.paper_dir(a).mkdir(parents=True)
    storage.write_meta(make_meta(a))
    b = allocate_paper_id(storage, year=2024, slug_hint="vla-paper")
    assert a == "2024-vla-paper"
    assert b == "2024-vla-paper-2"


def test_paper_dir_paths(tmp_path):
    storage = PaperStorage(tmp_path)
    pdir = storage.paper_dir("2024-x")
    assert pdir == tmp_path / "papers" / "2024-x"
    assert storage.source_pdf_path("2024-x") == pdir / "source.pdf"
    assert storage.full_md_path("2024-x") == pdir / "full.md"
    assert storage.notes_md_path("2024-x") == pdir / "notes.md"
    assert storage.meta_json_path("2024-x") == pdir / "meta.json"


def test_write_then_read_meta(tmp_path):
    storage = PaperStorage(tmp_path)
    storage.paper_dir("2024-x").mkdir(parents=True)
    storage.write_meta(make_meta("2024-x"))
    m = storage.read_meta("2024-x")
    assert m.paper_id == "2024-x"


def test_list_paper_ids(tmp_path):
    storage = PaperStorage(tmp_path)
    for pid in ("2024-a", "2024-b"):
        storage.paper_dir(pid).mkdir(parents=True)
        storage.write_meta(make_meta(pid))
    assert sorted(storage.list_paper_ids()) == ["2024-a", "2024-b"]


def test_find_by_hash(tmp_path):
    storage = PaperStorage(tmp_path)
    storage.paper_dir("2024-a").mkdir(parents=True)
    storage.write_meta(make_meta("2024-a", hash_="h1"))
    assert storage.find_by_hash("h1") == "2024-a"
    assert storage.find_by_hash("nope") is None
