"""Pass 2: synthesize an answer from per-paper notes."""
from __future__ import annotations

import re
from dataclasses import dataclass

from lib.llm.base import LLMClient


_SYSTEM = """\
You answer technical questions about autonomous-driving research papers \
using ONLY the per-paper notes provided. Cite each claim with the \
paper_id in square brackets, e.g. [2024-a]. If the notes do not contain \
the answer, say so directly.\
"""

_USER_TEMPLATE = """\
USER QUESTION:
{question}

PAPER NOTES (one block per paper):
{blocks}

Answer the question, citing paper_ids in [brackets].
"""

_CITE_RE = re.compile(r"\[([A-Za-z0-9][A-Za-z0-9_\-]*)\]")


@dataclass
class AnswerResult:
    answer: str
    cited_paper_ids: list[str]


def answer_from_notes(
    *, question: str, notes_by_id: dict[str, str], llm: LLMClient,
    max_tokens: int = 2048,
) -> AnswerResult:
    if not notes_by_id:
        return AnswerResult(
            answer="No library hit. The wiki has no relevant entries for this question.",
            cited_paper_ids=[],
        )
    blocks = "\n\n".join(
        f"[{pid}]\n{notes}" for pid, notes in notes_by_id.items()
    )
    user = _USER_TEMPLATE.format(question=question, blocks=blocks)
    text = llm.complete(system=_SYSTEM, user=user, max_tokens=max_tokens)
    cited = []
    for m in _CITE_RE.finditer(text):
        pid = m.group(1)
        if pid in notes_by_id and pid not in cited:
            cited.append(pid)
    return AnswerResult(answer=text, cited_paper_ids=cited)
