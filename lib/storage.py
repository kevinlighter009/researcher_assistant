"""Filesystem layer for papers/. meta.json is the source of truth."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Optional

from lib.models import PaperMeta


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def slugify(text: str) -> str:
    if not text:
        return "unknown"
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ascii", "ignore").decode("ascii")
    ascii_text = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return ascii_text or "unknown"


class PaperStorage:
    """Directory layout: <root>/papers/<paper_id>/{source.pdf,full.md,notes.md,meta.json}."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    @property
    def papers_root(self) -> Path:
        return self.data_dir / "papers"

    def paper_dir(self, paper_id: str) -> Path:
        return self.papers_root / paper_id

    def source_pdf_path(self, paper_id: str) -> Path:
        return self.paper_dir(paper_id) / "source.pdf"

    def full_md_path(self, paper_id: str) -> Path:
        return self.paper_dir(paper_id) / "full.md"

    def notes_md_path(self, paper_id: str) -> Path:
        return self.paper_dir(paper_id) / "notes.md"

    def meta_json_path(self, paper_id: str) -> Path:
        return self.paper_dir(paper_id) / "meta.json"

    def write_meta(self, meta: PaperMeta) -> None:
        path = self.meta_json_path(meta.paper_id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(meta.model_dump_json(indent=2))
        tmp.replace(path)

    def read_meta(self, paper_id: str) -> PaperMeta:
        return PaperMeta.model_validate_json(self.meta_json_path(paper_id).read_text())

    def list_paper_ids(self) -> list[str]:
        if not self.papers_root.exists():
            return []
        return [p.name for p in self.papers_root.iterdir()
                if p.is_dir() and (p / "meta.json").exists()]

    def iter_metas(self) -> Iterable[PaperMeta]:
        for pid in self.list_paper_ids():
            yield self.read_meta(pid)

    def find_by_hash(self, h: str) -> Optional[str]:
        for m in self.iter_metas():
            if m.content_hash == h:
                return m.paper_id
        return None


def allocate_paper_id(storage: PaperStorage, year: int, slug_hint: str) -> str:
    base = f"{year}-{slugify(slug_hint)}"
    if not storage.paper_dir(base).exists():
        return base
    for i in range(2, 100):
        cand = f"{base}-{i}"
        if not storage.paper_dir(cand).exists():
            return cand
    raise RuntimeError(f"too many collisions on paper_id base {base}")
