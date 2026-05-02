"""argparse CLI: ingest, query, rebuild-index."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib.config import Config, load_config
from lib.indexing.rebuild import rebuild_wiki
from lib.indexing.writer import WikiPaths
from lib.ingestion.fetchers.upload import upload_fetch
from lib.llm.base import LLMClient
from lib.pipeline import ingest_pdf_and_index
from lib.query.orchestrator import query_wiki
from lib.storage import PaperStorage


def _make_llm_client(cfg: Config, backend: str | None) -> LLMClient:
    backend = backend or cfg.llm.default_backend
    if backend == "anthropic":
        if not cfg.anthropic_api_key:
            raise SystemExit("ANTHROPIC_API_KEY not set")
        from lib.llm.anthropic_client import AnthropicClient
        return AnthropicClient(
            api_key=cfg.anthropic_api_key,
            model=cfg.llm.anthropic.model,
            default_max_tokens=cfg.llm.anthropic.max_tokens,
            default_temperature=cfg.llm.anthropic.temperature,
        )
    if backend == "claude_code":
        from lib.llm.claude_code_client import ClaudeCodeClient
        return ClaudeCodeClient(binary=cfg.llm.claude_code.binary)
    raise SystemExit(f"unknown backend: {backend}")


def _wiki_paths(cfg: Config) -> WikiPaths:
    return WikiPaths(cfg.data_dir / "wiki")


def _storage(cfg: Config) -> PaperStorage:
    return PaperStorage(cfg.data_dir)


def cmd_ingest(args, cfg: Config) -> int:
    fetched = upload_fetch(Path(args.path))
    llm = _make_llm_client(cfg, args.backend)
    result = ingest_pdf_and_index(
        fetched=fetched, storage=_storage(cfg), wiki_paths=_wiki_paths(cfg),
        seed_taxonomy=cfg.seed_taxonomy, llm=llm,
        max_full_md_chars=cfg.ingest.max_full_md_chars,
    )
    print(result.message)
    return 0


def cmd_query(args, cfg: Config) -> int:
    llm = _make_llm_client(cfg, args.backend)
    out = query_wiki(
        question=args.question, storage=_storage(cfg),
        wiki_paths=_wiki_paths(cfg), llm=llm, max_papers=args.max_papers,
    )
    print(out.answer)
    if out.cited_paper_ids:
        print("\nCited:", ", ".join(out.cited_paper_ids))
    return 0


def cmd_rebuild_index(args, cfg: Config) -> int:
    n = rebuild_wiki(
        _storage(cfg), _wiki_paths(cfg),
        seed_taxonomy=cfg.seed_taxonomy,
    )
    print(f"rebuilt wiki from {n} papers")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="personal_library")
    p.add_argument("--backend", default=None,
                   help="override llm backend (anthropic|claude_code)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("ingest", help="ingest a local PDF")
    pi.add_argument("path")
    pi.set_defaults(func=cmd_ingest)

    pq = sub.add_parser("query", help="query the wiki")
    pq.add_argument("question")
    pq.add_argument("--max-papers", type=int, default=5)
    pq.set_defaults(func=cmd_query)

    pr = sub.add_parser("rebuild-index",
                        help="regenerate wiki/ from papers/*/meta.json")
    pr.set_defaults(func=cmd_rebuild_index)

    args = p.parse_args(argv)
    cfg = load_config()
    return args.func(args, cfg)


if __name__ == "__main__":
    sys.exit(main())
