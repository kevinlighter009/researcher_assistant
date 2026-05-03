"""BM25-based content search over chunked Markdown files.

This module is intentionally independent of ``lib.indexing`` (which
generates the wiki) and ``lib.query`` (which routes LLM questions). It
gives the UI a content-search-with-ranking primitive without introducing
any model dependency: rank-bm25 is pure Python.

Tokenization is intentionally simple and shared between corpus and
query so kebab-case keywords from distillations (e.g. ``diffusion-policy``)
match as written.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from rank_bm25 import BM25Okapi


# ---- Tokenization -------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    """Lowercased word-ish tokens; preserves ``a-b`` and ``a_b`` joiners.

    Used for both corpus and query so the query "diffusion-policy" hits
    chunks that wrote it the same way.
    """
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


# ---- Data classes -------------------------------------------------------


@dataclass
class Chunk:
    """A piece of a Markdown file. One chunk per ``## `` section, plus a
    leading 'preamble' chunk for content before the first H2."""

    file_path: str  # repo-relative path as a string
    heading: str    # "" for preamble, else the H2 text
    text: str       # raw chunk text including the heading line


@dataclass
class SearchHit:
    file_path: str
    heading: str
    score: float
    snippet: str


# ---- Chunking -----------------------------------------------------------

_H2_RE = re.compile(r"^## (.+)$", re.MULTILINE)


def _split_by_h2(text: str) -> list[tuple[str, str]]:
    """Return ``[(heading, chunk_text), ...]``.

    Anything before the first H2 is a preamble chunk with heading ``""``.
    Files with no H2 produce a single ``("", text)`` pair.
    """
    matches = list(_H2_RE.finditer(text))
    if not matches:
        return [("", text)] if text.strip() else []

    out: list[tuple[str, str]] = []
    first = matches[0]
    preamble = text[: first.start()]
    if preamble.strip():
        out.append(("", preamble))

    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        heading = m.group(1).strip()
        chunk_text = text[start:end]
        out.append((heading, chunk_text))
    return out


# ---- Index --------------------------------------------------------------


@dataclass
class SearchIndex:
    """BM25 index over a list of Chunks. Persistable to a single JSON
    file holding chunks + corpus tokens; BM25 itself is rebuilt from the
    tokens on load (cheap)."""

    chunks: list[Chunk] = field(default_factory=list)
    _tokens: list[list[str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._bm25: BM25Okapi | None = None
        self._refresh_bm25()

    # ---- Building -------------------------------------------------------

    @classmethod
    def build(cls, roots: list[Path], *, repo_root: Path) -> "SearchIndex":
        """Walk ``roots`` recursively, parse every ``*.md`` (skip
        ``MANIFEST.md``), produce one chunk per H2 section (plus optional
        preamble), tokenize, and return a SearchIndex.
        """
        chunks: list[Chunk] = []
        tokens: list[list[str]] = []
        seen: set[Path] = set()
        for root in roots:
            if not root.exists():
                continue
            for md_path in sorted(root.rglob("*.md")):
                if md_path.name == "MANIFEST.md":
                    continue
                if md_path in seen:
                    continue
                seen.add(md_path)
                try:
                    text = md_path.read_text()
                except OSError:
                    continue
                try:
                    rel = md_path.resolve().relative_to(repo_root.resolve())
                    rel_str = str(rel)
                except ValueError:
                    rel_str = str(md_path)
                for heading, body in _split_by_h2(text):
                    chunks.append(Chunk(
                        file_path=rel_str, heading=heading, text=body,
                    ))
                    tokens.append(tokenize(body))
        idx = cls(chunks=chunks, _tokens=tokens)
        return idx

    def _refresh_bm25(self) -> None:
        # BM25Okapi needs every document non-empty (token list); we
        # substitute a placeholder for empty chunks so the bm25 index
        # stays aligned with self.chunks. Also: BM25Okapi's IDF goes
        # negative when a term's document-frequency exceeds N/2, which
        # inverts ranking on small corpora. We floor the IDF at a small
        # positive epsilon — the standard remedy noted by the rank-bm25
        # authors and used widely in practice.
        if not self._tokens:
            self._bm25 = None
            return
        safe = [t if t else ["__empty__"] for t in self._tokens]
        bm = BM25Okapi(safe)
        eps = 0.25 * sum(bm.idf.values()) / max(1, len(bm.idf))
        # average_idf can itself be negative when most idf values are.
        # Floor with a small absolute positive instead in that case.
        floor = eps if eps > 0 else 1e-3
        for term, val in bm.idf.items():
            if val < floor:
                bm.idf[term] = floor
        self._bm25 = bm

    # ---- Persistence ----------------------------------------------------

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chunks": [asdict(c) for c in self.chunks],
            "tokens": self._tokens,
        }
        path.write_text(json.dumps(payload))

    @classmethod
    def load(cls, path: Path) -> "SearchIndex":
        payload = json.loads(path.read_text())
        chunks = [Chunk(**c) for c in payload.get("chunks", [])]
        tokens = [list(t) for t in payload.get("tokens", [])]
        return cls(chunks=chunks, _tokens=tokens)

    # ---- Search ---------------------------------------------------------

    def search(self, query: str, *, k: int = 20) -> list[SearchHit]:
        q_tokens = tokenize(query)
        if not q_tokens or self._bm25 is None or not self.chunks:
            return []
        scores = self._bm25.get_scores(q_tokens)
        # Pair (score, idx), sort desc by score, take top-k of those > 0.
        ranked = sorted(
            ((float(s), i) for i, s in enumerate(scores) if s > 0.0),
            key=lambda x: x[0], reverse=True,
        )[:k]
        hits: list[SearchHit] = []
        for score, idx in ranked:
            chunk = self.chunks[idx]
            snippet = _make_snippet(chunk.text, q_tokens)
            hits.append(SearchHit(
                file_path=chunk.file_path,
                heading=chunk.heading,
                score=score,
                snippet=snippet,
            ))
        return hits


# ---- Snippet extraction -------------------------------------------------

_SNIPPET_LEN = 280


def _make_snippet(text: str, q_tokens: list[str]) -> str:
    """Return a ~280-char window centered on the highest-density region
    of ``q_tokens`` in ``text``. Whitespace is collapsed for display."""
    haystack = text
    lower = haystack.lower()
    positions: list[int] = []
    for tok in {t.lower() for t in q_tokens}:
        start = 0
        while True:
            j = lower.find(tok, start)
            if j < 0:
                break
            positions.append(j)
            start = j + max(1, len(tok))
    if not positions:
        return _collapse_ws(haystack[:_SNIPPET_LEN])

    # Pick the position with the most neighbours within a window.
    half = _SNIPPET_LEN // 2
    best_center = positions[0]
    best_density = -1
    for p in positions:
        density = sum(1 for q in positions if abs(q - p) <= half)
        if density > best_density:
            best_density = density
            best_center = p

    start = max(0, best_center - half)
    end = min(len(haystack), start + _SNIPPET_LEN)
    start = max(0, end - _SNIPPET_LEN)
    snippet = haystack[start:end]
    return _collapse_ws(snippet)


def _collapse_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()
