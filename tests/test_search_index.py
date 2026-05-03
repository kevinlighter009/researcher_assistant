"""Tests for lib.search.index — BM25 chunked Markdown search."""
from __future__ import annotations

from pathlib import Path

from lib.search import SearchHit, SearchIndex
from lib.search.index import tokenize


def _write(tmp_path: Path, rel: str, body: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)
    return p


def test_tokenize_handles_kebab_and_case():
    assert tokenize("Diffusion-Policy") == ["diffusion-policy"]
    assert tokenize("BEV foo_bar") == ["bev", "foo_bar"]


def test_build_chunks_per_h2_section(tmp_path):
    body = (
        "preamble line one\n"
        "preamble line two\n\n"
        "## Alpha\n"
        "alpha body\n\n"
        "## Beta\n"
        "beta body\n\n"
        "## Gamma\n"
        "gamma body\n"
    )
    _write(tmp_path, "doc.md", body)
    idx = SearchIndex.build([tmp_path], repo_root=tmp_path)
    headings = [c.heading for c in idx.chunks]
    # Preamble + 3 H2s = 4 chunks.
    assert len(idx.chunks) == 4
    assert headings == ["", "Alpha", "Beta", "Gamma"]
    # H2 chunks contain their heading line.
    alpha = next(c for c in idx.chunks if c.heading == "Alpha")
    assert alpha.text.startswith("## Alpha")
    assert "alpha body" in alpha.text


def test_build_handles_no_h2(tmp_path):
    _write(tmp_path, "flat.md", "just some prose without headings\n")
    idx = SearchIndex.build([tmp_path], repo_root=tmp_path)
    assert len(idx.chunks) == 1
    assert idx.chunks[0].heading == ""
    assert "just some prose" in idx.chunks[0].text


def test_search_ranks_relevant_first(tmp_path):
    _write(
        tmp_path,
        "many.md",
        "## Topic\ndiffusion diffusion diffusion diffusion diffusion model\n",
    )
    _write(
        tmp_path,
        "few.md",
        "## Topic\nthis paper barely mentions diffusion in passing\n",
    )
    idx = SearchIndex.build([tmp_path], repo_root=tmp_path)
    hits = idx.search("diffusion", k=10)
    assert hits, "expected at least one hit"
    assert hits[0].file_path.endswith("many.md")
    # Relative ordering by score.
    if len(hits) > 1:
        assert hits[0].score >= hits[1].score


def test_search_returns_snippet_with_query_term(tmp_path):
    body = (
        "## BEV section\n"
        + ("filler text. " * 30)
        + "this section discusses Diffusion-Policy training in detail. "
        + ("more filler. " * 30)
    )
    _write(tmp_path, "snip.md", body)
    idx = SearchIndex.build([tmp_path], repo_root=tmp_path)
    hits = idx.search("diffusion-policy")
    assert hits
    assert "diffusion-policy" in hits[0].snippet.lower()
    assert len(hits[0].snippet) <= 320  # ~280 plus a small slack


def test_search_filters_zero_scores(tmp_path):
    _write(tmp_path, "a.md", "## H\nalpha beta gamma\n")
    idx = SearchIndex.build([tmp_path], repo_root=tmp_path)
    hits = idx.search("zzzzzzqqqqqq")
    assert hits == []


def test_save_load_round_trip(tmp_path):
    _write(tmp_path, "a.md", "## H\ndiffusion policy training pipeline\n")
    _write(tmp_path, "b.md", "## H\nbev queries for perception\n")
    idx = SearchIndex.build([tmp_path], repo_root=tmp_path)
    out = tmp_path / ".search_index.json"
    idx.save(out)
    loaded = SearchIndex.load(out)
    assert len(loaded.chunks) == len(idx.chunks)
    h1 = idx.search("diffusion", k=5)
    h2 = loaded.search("diffusion", k=5)
    assert [(h.file_path, h.heading) for h in h1] == \
           [(h.file_path, h.heading) for h in h2]
    # Hits are SearchHit instances.
    assert all(isinstance(h, SearchHit) for h in h2)


def test_skip_manifest_md(tmp_path):
    _write(
        tmp_path,
        "MANIFEST.md",
        "## Manifest\nzebraflagellum unique-token-only-here\n",
    )
    _write(tmp_path, "real.md", "## Real\nordinary content\n")
    idx = SearchIndex.build([tmp_path], repo_root=tmp_path)
    files = {c.file_path for c in idx.chunks}
    assert all("MANIFEST.md" not in f for f in files)
    hits = idx.search("zebraflagellum")
    assert hits == []


def test_file_paths_are_repo_relative(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    _write(sub, "x.md", "## H\nhello world\n")
    idx = SearchIndex.build([sub], repo_root=tmp_path)
    assert idx.chunks
    for c in idx.chunks:
        # Stored path is relative (no leading slash, no tmp_path prefix).
        assert not c.file_path.startswith("/")
        assert str(tmp_path) not in c.file_path
        assert c.file_path.startswith("sub/")
