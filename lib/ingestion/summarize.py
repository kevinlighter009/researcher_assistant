"""LLM-driven summarization: full.md -> SummaryResult."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from lib.llm.base import LLMClient


_SYSTEM = """\
You are an indexing assistant for a research-paper wiki on autonomous driving.
You read a paper's extracted text and emit a strict JSON object describing it.
Be precise, factual, and concise.
"""

_USER_TEMPLATE = """\
Paper text (may be truncated):
---BEGIN PAPER---
{full_md}
---END PAPER---

Available primary categories (pick exactly one of these for primary_category):
{taxonomy_list}

Return ONLY a JSON object with these exact keys:
{{
  "title": str,
  "authors": [str, ...],
  "year": int,
  "primary_category": str,           // MUST be one of the listed categories
  "secondary_categories": [str, ...],
  "keywords": [str, ...],            // 3-8 short keywords
  "one_line_summary": str,           // <= 200 chars, technical, no fluff
  "notes_md": str                    // 300-500 word markdown: Problem, Method, Key Results, Novelty
}}

No prose, no code fences. Just the JSON object.
"""


@dataclass
class SummaryResult:
    title: str
    authors: list[str]
    year: int
    primary_category: str
    secondary_categories: list[str]
    keywords: list[str]
    one_line_summary: str
    notes_md: str


def _strip_code_fences(s: str) -> str:
    s = s.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", s, re.DOTALL)
    return m.group(1).strip() if m else s


def summarize_paper(
    *, full_md: str, seed_taxonomy: list[str], llm: LLMClient,
    max_tokens: int = 4096,
) -> SummaryResult:
    user = _USER_TEMPLATE.format(
        full_md=full_md,
        taxonomy_list="\n".join(f"- {c}" for c in seed_taxonomy),
    )
    raw = llm.complete(system=_SYSTEM, user=user, max_tokens=max_tokens)
    raw = _strip_code_fences(raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON: {e}") from e

    primary = data.get("primary_category", "misc")
    if primary not in seed_taxonomy:
        primary = "misc" if "misc" in seed_taxonomy else seed_taxonomy[-1]

    return SummaryResult(
        title=data["title"],
        authors=list(data.get("authors", [])),
        year=int(data["year"]),
        primary_category=primary,
        secondary_categories=list(data.get("secondary_categories", [])),
        keywords=list(data.get("keywords", [])),
        one_line_summary=data["one_line_summary"],
        notes_md=data["notes_md"],
    )
