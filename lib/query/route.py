"""Pass 1: pick relevant paper_ids from the wiki index given a question."""
from __future__ import annotations

import json
import re

from lib.llm.base import LLMClient


_SYSTEM = """\
You are a routing assistant for a research-paper wiki. \
Given the user's question and the wiki index, return the paper_ids \
most likely to help answer the question. Be selective.\
"""

_USER_TEMPLATE = """\
USER QUESTION:
{question}

WIKI INDEX (one row per paper):
{index_md}

Return ONLY a JSON object of the form: {{"paper_ids": ["id1", "id2", ...]}}.
Pick at most {max_papers} ids. If nothing in the index seems relevant, \
return {{"paper_ids": []}}.
"""

_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)
_ROW_ID_RE = re.compile(r"^\|\s*([^\s|]+)\s*\|", re.MULTILINE)


def _known_ids(index_md: str) -> set[str]:
    ids = set(_ROW_ID_RE.findall(index_md))
    ids.discard("paper_id")  # header
    ids.discard("----------")  # separator
    return ids


def route_query(
    *, question: str, index_md: str, llm: LLMClient, max_papers: int = 5,
) -> list[str]:
    user = _USER_TEMPLATE.format(
        question=question, index_md=index_md, max_papers=max_papers,
    )
    raw = llm.complete(system=_SYSTEM, user=user)
    raw = raw.strip()
    m = _FENCE_RE.match(raw)
    if m:
        raw = m.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    ids = data.get("paper_ids", []) or []
    known = _known_ids(index_md)
    filtered = [pid for pid in ids if pid in known]
    return filtered[:max_papers]
