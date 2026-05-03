"""Generate the wiki from distilled paper Markdown files.

Source files live under ``doc/distilled/<category>/<stem>.md`` with the
schema produced by ``skills/paper-distillation/SKILL.md`` — YAML
front-matter plus body sections in fixed order, starting with
``## Keywords`` and including ``## Model Architecture``.

This module produces three outputs under ``<wiki_root>/``:

1. ``index.md`` — master pipe-table for routing.
2. ``categories/<cat>.md`` — per-category page that embeds each paper's
   full ``## Model Architecture`` section verbatim (architecture is the
   value-add of this wiki, so it is intentionally not compressed).
3. ``architectures.md`` — cross-reference of papers by inferred
   architecture pattern, tagged via heuristics on keywords + arch text
   (e.g. ``uses-vlm-backbone``, ``uses-diffusion-head``).

No LLM call is made here — the distillation MDs are the source of truth.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml


# --- Section headings the parser recognizes -------------------------------

_SECTION_HEADINGS = (
    "Keywords",
    "TL;DR",
    "Problem & Motivation",
    "Innovation Points",
    "Model Architecture",
    "Benchmark Results",
    "Limitations & Open Questions",
)


# --- Architecture-pattern heuristics --------------------------------------
# Each tag has a list of regex patterns; a paper matches the tag if ANY
# pattern hits its keywords or the body of its `## Model Architecture`
# section. Patterns are case-insensitive and matched as substrings/regex.
# Order roughly reflects priority (most specific first); a paper can carry
# multiple tags.

_ARCH_PATTERNS: dict[str, list[str]] = {
    "uses-vlm-backbone": [
        r"\bvlm\b", r"\bmllm\b", r"\bllava\b", r"\bqwen-?vl\b",
        r"\bllama\b", r"vision[- ]language", r"\bgpt-4\b",
    ],
    "uses-diffusion-head": [
        r"diffusion", r"denois", r"\bddim\b", r"\bddpm\b",
        r"score-matching", r"flow[- ]matching",
    ],
    "uses-bev-transformer": [
        r"\bbev\b", r"deformable[- ]attention",
        r"bev[- ]former", r"bev[- ]queries",
    ],
    "uses-occupancy-grid": [
        r"\boccupancy\b", r"\boccworld\b", r"\bocc3d\b",
        r"3d occupancy",
    ],
    "uses-world-model": [
        r"world[- ]model", r"future video",
        r"video[- ]gen", r"video diffusion",
    ],
    "uses-cnn-backbone": [
        r"\bresnet-?\d", r"\befficientnet\b", r"\bconvnext\b",
        r"\bswin\b", r"\bvit\b",
    ],
    "uses-trajectory-anchors": [
        r"trajectory anchor", r"k-?means anchor",
        r"anchor(ed)? gaussian", r"meta[- ]action",
    ],
    "uses-classical-planner": [
        r"classical planner", r"rule-?based planner",
        r"slow[- ]fast", r"hybrid (planner|policy)",
    ],
}


# --- Data model -----------------------------------------------------------

@dataclass
class DistilledPaper:
    """A parsed distillation file. ``front_matter`` holds the YAML; ``sections``
    maps section headings to body text."""

    path: Path
    front_matter: dict
    sections: dict[str, str] = field(default_factory=dict)

    @property
    def paper_id(self) -> str:
        return str(self.front_matter.get("paper_id", ""))

    @property
    def title(self) -> str:
        return str(self.front_matter.get("title", ""))

    @property
    def year(self) -> int:
        return int(self.front_matter.get("year", 0) or 0)

    @property
    def venue(self) -> str:
        return str(self.front_matter.get("venue", "") or "")

    @property
    def primary_category(self) -> str:
        return str(self.front_matter.get("primary_category", "misc") or "misc")

    @property
    def keywords(self) -> list[str]:
        kws = self.front_matter.get("keywords", []) or []
        return [str(k) for k in kws]

    @property
    def one_line_summary(self) -> str:
        return str(self.front_matter.get("one_line_summary", "") or "")

    @property
    def url(self) -> str:
        return str(self.front_matter.get("url", "") or "")

    @property
    def architecture(self) -> str:
        return self.sections.get("Model Architecture", "").strip()


# --- Parser ---------------------------------------------------------------

_FRONT_MATTER_RE = re.compile(
    r"\A---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL,
)


def parse_distilled_md(path: Path) -> DistilledPaper:
    """Parse one distillation Markdown file into a :class:`DistilledPaper`.

    Raises ``ValueError`` if the file does not start with YAML front-matter
    or if the front-matter is not a YAML mapping.
    """
    text = Path(path).read_text()
    m = _FRONT_MATTER_RE.match(text)
    if not m:
        raise ValueError(f"{path}: missing YAML front-matter")
    fm_text, body = m.group(1), m.group(2)
    front_matter = yaml.safe_load(fm_text)
    if not isinstance(front_matter, dict):
        raise ValueError(f"{path}: front-matter is not a mapping")
    sections = _split_sections(body)
    return DistilledPaper(path=Path(path), front_matter=front_matter, sections=sections)


def _split_sections(body: str) -> dict[str, str]:
    """Split a Markdown body into a mapping of ``## Heading`` -> content text."""
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = stripped[3:].strip()
            buf = []
        else:
            if current is not None:
                buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def discover_distilled(root: Path) -> list[DistilledPaper]:
    """Walk ``root`` recursively and parse every ``*.md`` (skipping
    ``MANIFEST.md``). Returns papers sorted by ``(primary_category, paper_id)``.
    """
    root = Path(root)
    if not root.exists():
        return []
    papers: list[DistilledPaper] = []
    for md in sorted(root.rglob("*.md")):
        if md.name == "MANIFEST.md":
            continue
        try:
            papers.append(parse_distilled_md(md))
        except ValueError:
            # Files without proper front-matter are skipped silently — the
            # caller can run a strict parser separately if they care.
            continue
    papers.sort(key=lambda p: (p.primary_category, p.paper_id))
    return papers


# --- Architecture-pattern tagging ----------------------------------------

def infer_arch_tags(paper: DistilledPaper) -> list[str]:
    """Return architecture-pattern tags that apply to ``paper``.

    Heuristic: case-insensitive substring/regex matching against the
    concatenation of keywords + ``## Model Architecture`` body. Tag order
    matches the global ``_ARCH_PATTERNS`` definition; duplicates removed.
    """
    haystack = " ".join(paper.keywords) + "\n" + paper.architecture
    haystack = haystack.lower()
    tags: list[str] = []
    for tag, patterns in _ARCH_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, haystack, flags=re.IGNORECASE):
                tags.append(tag)
                break
    return tags


def architecture_signature(paper: DistilledPaper) -> str:
    """Pull a single-line architecture summary from ``paper`` for at-a-glance
    indexing. Looks for a leading ``**Inputs:**``-style bolded label OR the
    first non-empty bulleted line, falling back to the first body line.
    """
    arch = paper.architecture
    if not arch:
        return ""
    for raw in arch.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^[-*]\s+", "", line)        # drop bullet
        line = line.strip()
        if not line:
            continue
        return line[:240]                           # cap length
    return ""


# --- Wiki generation ------------------------------------------------------

@dataclass
class WikiOutput:
    """Paths the generator wrote to (for the CLI to print)."""

    index_md: Path
    categories: list[Path]
    architectures_md: Path
    paper_count: int


_INDEX_HEADER = (
    "| paper_id | year | category | title | venue | one_line_summary | keywords |\n"
    "|----------|------|----------|-------|-------|------------------|----------|\n"
)


def _safe_md_cell(s: str) -> str:
    """Escape ``|`` and collapse newlines so a value is safe for a Markdown
    table cell."""
    return s.replace("|", "\\|").replace("\n", " ").strip()


def _index_row(p: DistilledPaper) -> str:
    return (
        f"| {p.paper_id} | {p.year} | {p.primary_category} | "
        f"{_safe_md_cell(p.title)} | {_safe_md_cell(p.venue)} | "
        f"{_safe_md_cell(p.one_line_summary)} | "
        f"{_safe_md_cell(', '.join(p.keywords))} |\n"
    )


def _category_entry(p: DistilledPaper) -> str:
    arxiv_link = f" — [{p.url}]({p.url})" if p.url else ""
    notes_link = f"../../{p.path.parent.parent.name}/{p.path.parent.name}/{p.path.name}"
    # Source-distilled link: relative path from wiki/categories/<cat>.md back
    # to the distilled file. Recipients may or may not have the docs/ tree;
    # we link to the source distilled MD file by relative path from wiki root.
    return (
        f"## {p.paper_id} — {p.title}\n"
        f"- **Venue / year:** {p.venue or 'arXiv'} / {p.year}\n"
        f"- **Summary:** {p.one_line_summary}\n"
        f"- **Keywords:** {', '.join(p.keywords)}\n"
        f"- **Architecture signature:** {architecture_signature(p)}\n"
        f"- **Architecture tags:** {', '.join(infer_arch_tags(p)) or '—'}\n"
        f"- **arXiv:** {p.url or '—'}{arxiv_link if False else ''}\n"
        f"- **Distilled MD:** `{p.path}`\n\n"
        f"### Model Architecture\n\n{p.architecture or '_(no architecture section)_'}\n\n"
        f"---\n\n"
    )


def _category_page(category: str, papers: list[DistilledPaper]) -> str:
    head = (
        f"# {category}\n\n"
        f"Papers categorized as `{category}`. Each entry includes the "
        f"full **Model Architecture** section from the source distillation.\n\n"
        f"({len(papers)} paper(s))\n\n"
    )
    body = "".join(_category_entry(p) for p in papers)
    return head + body


def _architectures_page(papers: list[DistilledPaper]) -> str:
    """Build the cross-reference page grouped by inferred architecture tag,
    plus a quick-scan view by primary category."""
    parts: list[str] = []
    parts.append(
        "# Architectures Cross-Reference\n\n"
        "Two views of the corpus, both centred on **model architecture**:\n\n"
        "1. **By inferred architecture tag** — heuristic clusters from "
        "keywords + the `## Model Architecture` section.\n"
        "2. **By primary category, with one-line architecture signature.**\n\n"
        "Tags are non-exclusive (a paper may carry several).\n\n"
    )

    # ----- 1. By tag -----
    parts.append("## By inferred architecture tag\n\n")
    by_tag: dict[str, list[DistilledPaper]] = {tag: [] for tag in _ARCH_PATTERNS}
    untagged: list[DistilledPaper] = []
    for p in papers:
        tags = infer_arch_tags(p)
        if not tags:
            untagged.append(p)
        for t in tags:
            by_tag[t].append(p)
    for tag in _ARCH_PATTERNS:
        bucket = by_tag[tag]
        if not bucket:
            continue
        parts.append(f"### `{tag}` ({len(bucket)})\n\n")
        for p in bucket:
            parts.append(
                f"- **{p.paper_id}** — {p.title}  \n"
                f"  _{p.primary_category} • {p.venue or 'arXiv'} {p.year}_  \n"
                f"  Architecture: {architecture_signature(p)}\n"
            )
        parts.append("\n")
    if untagged:
        parts.append(f"### `untagged` ({len(untagged)})\n\n")
        for p in untagged:
            parts.append(
                f"- **{p.paper_id}** — {p.title} _({p.primary_category})_\n"
            )
        parts.append("\n")

    # ----- 2. By category -----
    parts.append("## By primary category\n\n")
    by_cat: dict[str, list[DistilledPaper]] = {}
    for p in papers:
        by_cat.setdefault(p.primary_category, []).append(p)
    for cat in sorted(by_cat):
        bucket = by_cat[cat]
        parts.append(f"### `{cat}` ({len(bucket)})\n\n")
        parts.append(
            "| paper_id | title | tags | architecture (1-line) |\n"
            "|----------|-------|------|------------------------|\n"
        )
        for p in bucket:
            parts.append(
                f"| {p.paper_id} | {_safe_md_cell(p.title)} | "
                f"{_safe_md_cell(', '.join(infer_arch_tags(p)))} | "
                f"{_safe_md_cell(architecture_signature(p))} |\n"
            )
        parts.append("\n")

    return "".join(parts)


def generate_wiki_from_distilled(
    papers: Iterable[DistilledPaper],
    wiki_root: Path,
    *,
    seed_taxonomy: list[str] | None = None,
) -> WikiOutput:
    """Write ``index.md``, ``categories/<cat>.md`` and ``architectures.md``
    under ``wiki_root``. Existing files at those paths are overwritten;
    other files in ``wiki_root`` are left alone.

    If ``seed_taxonomy`` is supplied, an empty category page is created for
    every taxonomy entry that has no papers (useful for browsing).
    """
    papers = list(papers)
    wiki_root = Path(wiki_root)
    wiki_root.mkdir(parents=True, exist_ok=True)
    cat_dir = wiki_root / "categories"
    cat_dir.mkdir(parents=True, exist_ok=True)

    # ---- index.md ----
    index_md = wiki_root / "index.md"
    rows = "".join(_index_row(p) for p in papers)
    index_md.write_text(_INDEX_HEADER + rows)

    # ---- categories/<cat>.md ----
    by_cat: dict[str, list[DistilledPaper]] = {}
    for p in papers:
        by_cat.setdefault(p.primary_category, []).append(p)

    written_cats: list[Path] = []
    cats = set(by_cat) | set(seed_taxonomy or [])
    for cat in sorted(cats):
        path = cat_dir / f"{cat}.md"
        path.write_text(_category_page(cat, by_cat.get(cat, [])))
        written_cats.append(path)

    # ---- architectures.md ----
    arch_md = wiki_root / "architectures.md"
    arch_md.write_text(_architectures_page(papers))

    return WikiOutput(
        index_md=index_md,
        categories=written_cats,
        architectures_md=arch_md,
        paper_count=len(papers),
    )
