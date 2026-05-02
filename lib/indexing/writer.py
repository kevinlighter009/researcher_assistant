"""Write/update wiki/index.md and wiki/categories/<cat>.md."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lib.models import PaperMeta


_INDEX_HEADER = (
    "| paper_id | year | title | primary_category | one_line_summary | keywords |\n"
    "|----------|------|-------|------------------|------------------|----------|\n"
)


@dataclass
class WikiPaths:
    root: Path

    @property
    def index_md(self) -> Path:
        return self.root / "index.md"

    @property
    def categories_dir(self) -> Path:
        return self.root / "categories"

    def category_md(self, cat: str) -> Path:
        return self.categories_dir / f"{cat}.md"


def _index_row(m: PaperMeta) -> str:
    kws = ", ".join(m.keywords)
    return f"| {m.paper_id} | {m.year} | {m.title} | {m.primary_category} | {m.one_line_summary} | {kws} |\n"


def _category_entry(m: PaperMeta) -> str:
    return (
        f"## {m.paper_id} — {m.title}\n"
        f"- Year: {m.year}\n"
        f"- Summary: {m.one_line_summary}\n"
        f"- Keywords: {', '.join(m.keywords)}\n"
        f"- Notes: ../../papers/{m.paper_id}/notes.md\n\n"
    )


def _ensure_index(paths: WikiPaths) -> None:
    paths.root.mkdir(parents=True, exist_ok=True)
    if not paths.index_md.exists():
        paths.index_md.write_text(_INDEX_HEADER)


def _ensure_category(paths: WikiPaths, cat: str) -> None:
    paths.categories_dir.mkdir(parents=True, exist_ok=True)
    cat_path = paths.category_md(cat)
    if not cat_path.exists():
        cat_path.write_text(f"# {cat}\n\nPapers categorized as `{cat}`.\n\n")


def _remove_paper_from_index(text: str, paper_id: str) -> str:
    return "".join(
        line for line in text.splitlines(keepends=True)
        if not line.startswith(f"| {paper_id} |")
    )


def _remove_paper_from_category(text: str, paper_id: str) -> str:
    # An entry starts with "## <paper_id> —" and ends at the next "## " or EOF.
    pattern = re.compile(
        rf"(^## {re.escape(paper_id)} — .*?(?=^## |\Z))",
        re.DOTALL | re.MULTILINE,
    )
    return pattern.sub("", text)


def upsert_paper_in_wiki(meta: PaperMeta, paths: WikiPaths) -> None:
    _ensure_index(paths)
    # 1) update master index
    cur = paths.index_md.read_text()
    cur = _remove_paper_from_index(cur, meta.paper_id)
    if not cur.endswith("\n"):
        cur += "\n"
    cur += _index_row(meta)
    paths.index_md.write_text(cur)

    # 2) remove from any old category file (cheap scan)
    if paths.categories_dir.exists():
        for cat_file in paths.categories_dir.glob("*.md"):
            if cat_file.name == f"{meta.primary_category}.md":
                continue
            text = cat_file.read_text()
            new = _remove_paper_from_category(text, meta.paper_id)
            if new != text:
                cat_file.write_text(new)

    # 3) write into target category file
    _ensure_category(paths, meta.primary_category)
    cat_path = paths.category_md(meta.primary_category)
    text = cat_path.read_text()
    text = _remove_paper_from_category(text, meta.paper_id)
    if not text.endswith("\n\n"):
        text = text.rstrip() + "\n\n"
    text += _category_entry(meta)
    cat_path.write_text(text)
