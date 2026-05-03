from __future__ import annotations
from pathlib import Path

import pytest

from lib.distillation.sync import (
    PaperEntry,
    SyncStatus,
    check_sync,
    delete_orphan_distillations,
)


def _touch(path: Path, content: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_check_sync_classifies_correctly(tmp_path):
    papers = tmp_path / "papers"
    distilled = tmp_path / "distilled"

    # Category vla:
    #   - in-sync pair (a)
    #   - missing-md (b: pdf only)
    _touch(papers / "vla" / "a.pdf", "pdf-a")
    _touch(distilled / "vla" / "a.md", "md-a")
    _touch(papers / "vla" / "b.pdf", "pdf-b")

    # Category llm:
    #   - orphan-md (c: md only)
    #   - in-sync pair (d)
    _touch(distilled / "llm" / "c.md", "md-c")
    _touch(papers / "llm" / "d.pdf", "pdf-d")
    _touch(distilled / "llm" / "d.md", "md-d")

    status = check_sync(papers, distilled)

    in_sync_keys = {(e.category, e.stem) for e in status.in_sync}
    missing_keys = {(e.category, e.stem) for e in status.missing}
    orphan_keys = {(e.category, e.stem) for e in status.orphans}

    assert in_sync_keys == {("vla", "a"), ("llm", "d")}
    assert missing_keys == {("vla", "b")}
    assert orphan_keys == {("llm", "c")}

    # Sorted by (category, stem)
    keys = [(e.category, e.stem) for e in status.entries]
    assert keys == sorted(keys)


def test_check_sync_skips_manifest_md(tmp_path):
    papers = tmp_path / "papers"
    distilled = tmp_path / "distilled"

    _touch(distilled / "vla" / "MANIFEST.md", "manifest")
    _touch(papers / "vla" / "a.pdf", "pdf-a")
    _touch(distilled / "vla" / "a.md", "md-a")

    status = check_sync(papers, distilled)
    keys = {(e.category, e.stem) for e in status.entries}
    # MANIFEST.md must not appear at all (not as orphan, not as entry)
    assert ("vla", "MANIFEST") not in keys
    assert keys == {("vla", "a")}
    assert status.orphans == []


def test_check_sync_handles_empty_or_missing_root(tmp_path):
    # Both empty dirs
    papers = tmp_path / "papers"
    distilled = tmp_path / "distilled"
    papers.mkdir()
    distilled.mkdir()
    status = check_sync(papers, distilled)
    assert status.entries == []

    # One missing entirely (no crash)
    missing_papers = tmp_path / "no_such_papers"
    status2 = check_sync(missing_papers, distilled)
    assert status2.entries == []

    missing_distilled = tmp_path / "no_such_distilled"
    status3 = check_sync(papers, missing_distilled)
    assert status3.entries == []

    # Both missing
    status4 = check_sync(tmp_path / "x", tmp_path / "y")
    assert status4.entries == []


def test_check_sync_only_one_category_level(tmp_path):
    papers = tmp_path / "papers"
    distilled = tmp_path / "distilled"

    # Direct child: should be picked up
    _touch(papers / "vla" / "good.pdf", "pdf")
    # Sub-subdirectory: should be ignored
    _touch(papers / "vla" / "subdir" / "x.pdf", "pdf")
    _touch(distilled / "vla" / "subdir" / "y.md", "md")

    status = check_sync(papers, distilled)
    keys = {(e.category, e.stem) for e in status.entries}
    assert keys == {("vla", "good")}


def test_delete_orphan_distillations(tmp_path):
    papers = tmp_path / "papers"
    distilled = tmp_path / "distilled"

    md1 = _touch(distilled / "llm" / "orphan1.md", "m1")
    md2 = _touch(distilled / "vla" / "orphan2.md", "m2")
    pdf_keep = _touch(papers / "vla" / "keep.pdf", "pdf-keep")
    md_keep = _touch(distilled / "vla" / "keep.md", "md-keep")

    orphan1 = PaperEntry(category="llm", stem="orphan1", pdf_path=None, md_path=md1)
    orphan2 = PaperEntry(category="vla", stem="orphan2", pdf_path=None, md_path=md2)
    skip_no_md = PaperEntry(category="x", stem="z", pdf_path=None, md_path=None)

    deleted = delete_orphan_distillations([orphan1, orphan2, skip_no_md])

    assert set(deleted) == {md1, md2}
    assert not md1.exists()
    assert not md2.exists()
    # PDFs and other md untouched
    assert pdf_keep.exists()
    assert md_keep.exists()


def test_paper_entry_properties(tmp_path):
    pdf = tmp_path / "p.pdf"
    md = tmp_path / "m.md"

    both = PaperEntry(category="c", stem="s", pdf_path=pdf, md_path=md)
    assert both.has_pdf and both.has_md
    assert both.in_sync
    assert not both.orphan
    assert not both.missing

    pdf_only = PaperEntry(category="c", stem="s", pdf_path=pdf, md_path=None)
    assert pdf_only.has_pdf and not pdf_only.has_md
    assert not pdf_only.in_sync
    assert not pdf_only.orphan
    assert pdf_only.missing

    md_only = PaperEntry(category="c", stem="s", pdf_path=None, md_path=md)
    assert not md_only.has_pdf and md_only.has_md
    assert not md_only.in_sync
    assert md_only.orphan
    assert not md_only.missing

    neither = PaperEntry(category="c", stem="s", pdf_path=None, md_path=None)
    assert not neither.has_pdf and not neither.has_md
    assert not neither.in_sync
    assert not neither.orphan
    assert not neither.missing
