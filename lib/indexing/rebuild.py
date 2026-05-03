"""Regenerate wiki/ from papers/*/meta.json. Source of truth = meta.json."""
from __future__ import annotations

import shutil

from lib.indexing.writer import WikiPaths, upsert_paper_in_wiki, _ensure_category, _ensure_index
from lib.storage import PaperStorage


def rebuild_wiki(
    storage: PaperStorage, paths: WikiPaths, *, seed_taxonomy: list[str],
) -> int:
    if paths.root.exists():
        shutil.rmtree(paths.root)
    _ensure_index(paths)
    for cat in seed_taxonomy:
        _ensure_category(paths, cat)
    count = 0
    for meta in storage.iter_metas():
        upsert_paper_in_wiki(meta, paths)
        count += 1
    return count
