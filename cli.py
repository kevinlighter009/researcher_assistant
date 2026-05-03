"""argparse CLI: ingest, query, rebuild-index."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib.config import Config, load_config
from lib.distillation.sync import (
    check_sync,
    delete_orphan_distillations,
)
from lib.indexing.from_distilled import (
    discover_distilled,
    generate_wiki_from_distilled,
)
from lib.indexing.rebuild import rebuild_wiki
from lib.indexing.writer import WikiPaths
from lib.ingestion.fetchers.upload import upload_fetch
from lib.llm.base import LLMClient
from lib.pipeline import ingest_pdf_and_index
from lib.query.orchestrator import query_wiki
from lib.search import SearchIndex
from lib.storage import PaperStorage


_DEFAULT_SEARCH_INDEX = Path("data/.search_index.json")
_DEFAULT_SEARCH_ROOTS = (Path("data/wiki"), Path("doc/distilled"))


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


def _papers_root() -> Path:
    return Path("doc/papers")


def _distilled_root() -> Path:
    return Path("doc/distilled")


def cmd_distill_check(args, cfg: Config) -> int:
    status = check_sync(_papers_root(), _distilled_root())
    print(f"in sync:               {len(status.in_sync)}")
    print(f"missing distillation:  {len(status.missing)}")
    print(f"orphan distillation:   {len(status.orphans)}")
    if status.missing:
        print("\nmissing:")
        for e in status.missing:
            print(f"  - {e.category}/{e.stem}.pdf")
    if status.orphans:
        print("\norphans:")
        for e in status.orphans:
            print(f"  - {e.category}/{e.stem}.md")
    return 0


def cmd_distill_clean(args, cfg: Config) -> int:
    status = check_sync(_papers_root(), _distilled_root())
    if not status.orphans:
        print("no orphans to clean")
        return 0
    if not args.yes:
        print(f"would delete {len(status.orphans)} orphan(s); pass --yes to actually delete")
        for e in status.orphans:
            print(f"  - {e.md_path}")
        return 0
    removed = delete_orphan_distillations(status.orphans)
    print(f"deleted {len(removed)} orphan distillation(s)")
    for p in removed:
        print(f"  - {p}")
    return 0


def cmd_distill_run(args, cfg: Config) -> int:
    # api_distill is imported lazily so this command works even before the
    # api_distill module fully lands. If it's missing the user gets a clear
    # error pointing at the right thing.
    try:
        from lib.distillation.api_distill import distill_pdf_via_api
    except ImportError as e:
        print(f"distill-run requires lib.distillation.api_distill: {e}")
        return 2

    llm = _make_llm_client(cfg, args.backend)
    status = check_sync(_papers_root(), _distilled_root())
    targets = status.missing
    if args.only:
        only = set(args.only)
        targets = [e for e in targets if f"{e.category}/{e.stem}" in only]
    if not targets:
        print("no missing distillations to run")
        return 0
    print(f"distilling {len(targets)} paper(s) using backend={args.backend or cfg.llm.default_backend}")
    failures: list[tuple[str, str]] = []
    for i, e in enumerate(targets, start=1):
        out_path = _distilled_root() / e.category / f"{e.stem}.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            res = distill_pdf_via_api(
                pdf_path=e.pdf_path,
                output_path=out_path,
                llm=llm,
                max_full_md_chars=cfg.ingest.max_full_md_chars,
            )
            print(f"[{i}/{len(targets)}] OK  {e.category}/{e.stem} -> "
                  f"{res.paper_id} ({res.primary_category}, {res.word_count} words)")
        except Exception as exc:  # pylint: disable=broad-except
            failures.append((f"{e.category}/{e.stem}", str(exc)))
            print(f"[{i}/{len(targets)}] FAIL {e.category}/{e.stem}: {exc}")
    if failures:
        print(f"\n{len(failures)} failure(s):")
        for k, v in failures:
            print(f"  - {k}: {v}")
        return 1
    return 0


def _build_search_index(out: Path) -> SearchIndex:
    repo_root = Path.cwd()
    roots = [repo_root / r for r in _DEFAULT_SEARCH_ROOTS]
    idx = SearchIndex.build(roots, repo_root=repo_root)
    idx.save(out)
    return idx


def cmd_search_index(args, cfg: Config) -> int:
    out = Path(args.out) if args.out else _DEFAULT_SEARCH_INDEX
    if args.rebuild or not out.exists():
        idx = _build_search_index(out)
        print(f"built search index: {len(idx.chunks)} chunks -> {out}")
    else:
        idx = SearchIndex.load(out)
        print(f"loaded existing index: {len(idx.chunks)} chunks from {out}")
    return 0


def cmd_search(args, cfg: Config) -> int:
    out = Path(args.index) if args.index else _DEFAULT_SEARCH_INDEX
    if not out.exists():
        idx = _build_search_index(out)
        print(f"(built fresh index: {len(idx.chunks)} chunks)")
    else:
        idx = SearchIndex.load(out)
    hits = idx.search(args.query, k=args.k)
    if not hits:
        print("no hits")
        return 0
    for h in hits:
        heading = h.heading or "(preamble)"
        print(f"[score {h.score:6.2f}] {h.file_path}  -- {heading}")
        print(f"  {h.snippet}")
    return 0


def cmd_wiki_from_distilled(args, cfg: Config) -> int:
    distilled_dir = Path(args.distilled_dir)
    out_dir = Path(args.out_dir) if args.out_dir else cfg.data_dir / "wiki"
    papers = discover_distilled(distilled_dir)
    if not papers:
        print(f"no distilled MDs found under {distilled_dir}")
        return 1
    out = generate_wiki_from_distilled(
        papers, out_dir, seed_taxonomy=cfg.seed_taxonomy,
    )
    print(f"wrote {out.paper_count} papers into {out_dir}")
    print(f"  index:         {out.index_md}")
    print(f"  categories:    {len(out.categories)} files in {out_dir}/categories/")
    print(f"  architectures: {out.architectures_md}")
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

    pw = sub.add_parser(
        "wiki-from-distilled",
        help="generate wiki/ from doc/distilled/<cat>/*.md (no LLM call)",
    )
    pw.add_argument("--distilled-dir", default="doc/distilled",
                    help="root containing per-category distilled MDs")
    pw.add_argument("--out-dir", default=None,
                    help="output wiki dir; defaults to <data_dir>/wiki")
    pw.set_defaults(func=cmd_wiki_from_distilled)

    pdc = sub.add_parser(
        "distill-check",
        help="diff doc/papers/ vs doc/distilled/; print missing+orphan",
    )
    pdc.set_defaults(func=cmd_distill_check)

    pdr = sub.add_parser(
        "distill-run",
        help="run API-driven distillation for missing PDFs (requires API key)",
    )
    pdr.add_argument("--only", action="append", default=None,
                     help="<category>/<stem> to limit to (repeatable)")
    pdr.set_defaults(func=cmd_distill_run)

    pdcl = sub.add_parser(
        "distill-clean",
        help="delete orphan distilled MDs (those without a matching PDF)",
    )
    pdcl.add_argument("--yes", action="store_true",
                      help="actually delete (otherwise dry-run)")
    pdcl.set_defaults(func=cmd_distill_clean)

    psi = sub.add_parser(
        "search-index",
        help="build/rebuild BM25 search index over wiki + distilled MDs",
    )
    psi.add_argument("--rebuild", action="store_true",
                     help="rebuild even if the index file exists")
    psi.add_argument("--out", default=None,
                     help=f"index output path (default {_DEFAULT_SEARCH_INDEX})")
    psi.set_defaults(func=cmd_search_index)

    ps = sub.add_parser("search", help="content-search the wiki corpus")
    ps.add_argument("query")
    ps.add_argument("--k", type=int, default=20, help="top-k hits (default 20)")
    ps.add_argument("--index", default=None,
                    help=f"index path (default {_DEFAULT_SEARCH_INDEX})")
    ps.set_defaults(func=cmd_search)

    args = p.parse_args(argv)
    cfg = load_config()
    return args.func(args, cfg)


if __name__ == "__main__":
    sys.exit(main())
