"""Two-pass query: route over wiki/index.md, then answer from notes.md."""
from __future__ import annotations

from dataclasses import dataclass

from lib.indexing.writer import WikiPaths
from lib.llm.base import LLMClient
from lib.query.answer import answer_from_notes
from lib.query.route import route_query
from lib.storage import PaperStorage


@dataclass
class QueryResult:
    answer: str
    routed_paper_ids: list[str]
    cited_paper_ids: list[str]


def query_wiki(
    *, question: str, storage: PaperStorage, wiki_paths: WikiPaths,
    llm: LLMClient, max_papers: int = 5,
) -> QueryResult:
    if not wiki_paths.index_md.exists():
        return QueryResult(
            answer="No library hit. The wiki has no entries yet.",
            routed_paper_ids=[], cited_paper_ids=[],
        )
    index_md = wiki_paths.index_md.read_text()
    routed = route_query(question=question, index_md=index_md,
                         llm=llm, max_papers=max_papers)
    if not routed:
        ar = answer_from_notes(question=question, notes_by_id={}, llm=llm)
        return QueryResult(answer=ar.answer, routed_paper_ids=[],
                           cited_paper_ids=[])
    notes_by_id: dict[str, str] = {}
    for pid in routed:
        np = storage.notes_md_path(pid)
        if np.exists():
            notes_by_id[pid] = np.read_text()
    ar = answer_from_notes(question=question, notes_by_id=notes_by_id, llm=llm)
    return QueryResult(
        answer=ar.answer, routed_paper_ids=routed,
        cited_paper_ids=ar.cited_paper_ids,
    )
