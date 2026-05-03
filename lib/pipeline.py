"""Thin façade combining ingestion + indexing for the CLI/UI."""
from __future__ import annotations

from lib.indexing.writer import WikiPaths, upsert_paper_in_wiki
from lib.ingestion.fetchers.upload import FetchedSource
from lib.ingestion.orchestrator import ingest_pdf
from lib.llm.base import LLMClient
from lib.models import IngestResult
from lib.storage import PaperStorage


def ingest_pdf_and_index(
    *,
    fetched: FetchedSource,
    storage: PaperStorage,
    wiki_paths: WikiPaths,
    seed_taxonomy: list[str],
    llm: LLMClient,
    max_full_md_chars: int,
) -> IngestResult:
    result = ingest_pdf(
        fetched=fetched, storage=storage,
        seed_taxonomy=seed_taxonomy, llm=llm,
        max_full_md_chars=max_full_md_chars,
    )
    if result.created:
        meta = storage.read_meta(result.paper_id)
        upsert_paper_in_wiki(meta, wiki_paths)
    return result
