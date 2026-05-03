from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PaperEntry:
    """A pdf/md pair keyed by (category, stem)."""

    category: str
    stem: str
    pdf_path: Path | None
    md_path: Path | None

    @property
    def has_pdf(self) -> bool:
        return self.pdf_path is not None

    @property
    def has_md(self) -> bool:
        return self.md_path is not None

    @property
    def in_sync(self) -> bool:
        return self.has_pdf and self.has_md

    @property
    def orphan(self) -> bool:
        return self.has_md and not self.has_pdf

    @property
    def missing(self) -> bool:
        return self.has_pdf and not self.has_md


@dataclass
class SyncStatus:
    entries: list[PaperEntry] = field(default_factory=list)

    @property
    def in_sync(self) -> list[PaperEntry]:
        return [e for e in self.entries if e.in_sync]

    @property
    def missing(self) -> list[PaperEntry]:
        return [e for e in self.entries if e.missing]

    @property
    def orphans(self) -> list[PaperEntry]:
        return [e for e in self.entries if e.orphan]


def _scan_one_level(root: Path, suffix: str) -> dict[tuple[str, str], Path]:
    """Return {(category, stem): path} for files at <root>/<category>/<stem><suffix>.

    Only direct children inside each category dir; sub-subdirectories ignored.
    Returns empty dict if root doesn't exist.
    """
    results: dict[tuple[str, str], Path] = {}
    if not root.exists() or not root.is_dir():
        return results
    for cat_dir in root.iterdir():
        if not cat_dir.is_dir():
            continue
        category = cat_dir.name
        for entry in cat_dir.iterdir():
            if not entry.is_file():
                continue
            if entry.suffix != suffix:
                continue
            results[(category, entry.stem)] = entry
    return results


def check_sync(papers_root: Path, distilled_root: Path) -> SyncStatus:
    """Walk both roots and produce a SyncStatus.

    PDFs found at <papers_root>/<cat>/<stem>.pdf.
    MDs found at <distilled_root>/<cat>/<stem>.md.
    Files named MANIFEST.md are ignored on the distilled side.
    Sub-subdirectories are NOT recursed (only one level of <category>).
    Sorted output: by (category, stem).
    """
    pdfs = _scan_one_level(papers_root, ".pdf")
    mds_raw = _scan_one_level(distilled_root, ".md")
    mds = {key: path for key, path in mds_raw.items() if key[1] != "MANIFEST"}

    keys = sorted(set(pdfs.keys()) | set(mds.keys()))
    entries = [
        PaperEntry(
            category=cat,
            stem=stem,
            pdf_path=pdfs.get((cat, stem)),
            md_path=mds.get((cat, stem)),
        )
        for (cat, stem) in keys
    ]
    return SyncStatus(entries=entries)


def delete_orphan_distillations(orphans: list[PaperEntry]) -> list[Path]:
    """Delete the .md file for each orphan entry. Returns the paths deleted.

    Caller is responsible for filtering to truly-orphan entries (we don't
    re-check here -- UI / CLI does the safety prompt). Skips entries with
    md_path is None.
    """
    deleted: list[Path] = []
    for entry in orphans:
        md = entry.md_path
        if md is None:
            continue
        try:
            md.unlink()
        except FileNotFoundError:
            continue
        deleted.append(md)
    return deleted
