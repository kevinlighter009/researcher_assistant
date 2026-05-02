from pathlib import Path

from lib.indexing.rebuild import rebuild_wiki
from lib.indexing.writer import WikiPaths
from lib.storage import PaperStorage
from lib.models import PaperMeta


def write_paper(storage, pid, cat="vla", year=2024):
    storage.paper_dir(pid).mkdir(parents=True)
    storage.write_meta(PaperMeta(
        paper_id=pid, title=f"T-{pid}", authors=[], year=year,
        primary_category=cat, ingested_at="2026-05-02T00:00:00Z",
        source_type="upload", content_hash=pid,
        one_line_summary=f"summary {pid}", notes_status="ok",
    ))


def test_rebuild_creates_wiki_from_metas(tmp_path):
    storage = PaperStorage(tmp_path)
    write_paper(storage, "2024-a", cat="vla")
    write_paper(storage, "2024-b", cat="world_model")
    paths = WikiPaths(tmp_path / "wiki")
    rebuild_wiki(storage, paths, seed_taxonomy=["vla", "world_model", "misc"])
    idx = paths.index_md.read_text()
    assert "2024-a" in idx and "2024-b" in idx
    assert "2024-a" in paths.category_md("vla").read_text()
    assert "2024-b" in paths.category_md("world_model").read_text()
    # seed taxonomy categories all exist as files (even if empty)
    assert paths.category_md("misc").exists()


def test_rebuild_overwrites_old_state(tmp_path):
    storage = PaperStorage(tmp_path)
    write_paper(storage, "2024-a", cat="vla")
    paths = WikiPaths(tmp_path / "wiki")
    paths.root.mkdir()
    paths.index_md.write_text("STALE CONTENT\n| 9999-zombie |\n")
    rebuild_wiki(storage, paths, seed_taxonomy=["vla", "misc"])
    idx = paths.index_md.read_text()
    assert "STALE" not in idx
    assert "9999-zombie" not in idx
    assert "2024-a" in idx
