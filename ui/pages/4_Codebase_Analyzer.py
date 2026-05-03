"""Codebase Analyzer — UI surface for the codebase-analyzer skill.

Walks a target codebase, asks the LLM (following the skill) to compare it
against the personal-library wiki, and renders the resulting
UPGRADE_PROPOSALS.md inline. Past runs are persisted under
``data/codebase_analyses/<repo>/<timestamp>.md`` so a researcher can revisit
or compare runs.
"""
from __future__ import annotations

import datetime as dt
import sys
import traceback
from pathlib import Path

import streamlit as st

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.codebase.analyze import (  # noqa: E402
    bundle_codebase,
    run_codebase_analysis,
)
from lib.config import load_config  # noqa: E402


st.set_page_config(
    page_title="Codebase Analyzer",
    page_icon=":mag:",
    layout="wide",
)
st.title("Codebase Analyzer")
st.caption(
    "Compare an existing codebase against the personal-library wiki and "
    "produce wiki-grounded upgrade proposals. Backed by the "
    "`codebase-analyzer` skill at `skills/codebase-analyzer/SKILL.md`."
)


cfg = load_config(_REPO_ROOT / "config")
SKILL_PATH = _REPO_ROOT / "skills" / "codebase-analyzer" / "SKILL.md"
WIKI_ROOT = _REPO_ROOT / cfg.data_dir / "wiki" if not cfg.data_dir.is_absolute() \
    else cfg.data_dir / "wiki"
DISTILLED_ROOT = _REPO_ROOT / "doc" / "distilled"
ANALYSES_ROOT = _REPO_ROOT / "data" / "codebase_analyses"


# ---- Sanity panel -----------------------------------------------------

with st.expander("Setup status", expanded=False):
    rows = [
        ("Skill",        SKILL_PATH,     SKILL_PATH.exists()),
        ("Wiki root",    WIKI_ROOT,      WIKI_ROOT.exists()),
        ("Distillations", DISTILLED_ROOT, DISTILLED_ROOT.exists()),
        ("Past runs",    ANALYSES_ROOT,  ANALYSES_ROOT.exists()),
    ]
    for label, path, ok in rows:
        marker = ":white_check_mark:" if ok else ":warning:"
        st.write(f"{marker} **{label}** — `{path.relative_to(_REPO_ROOT)}`")
    if not WIKI_ROOT.exists():
        st.warning(
            "Wiki not generated yet. Run `python cli.py wiki-from-distilled` "
            "before running an analysis — the skill cites paper_ids from the "
            "wiki and needs `architectures.md`, `taxonomy.md`, and the "
            "`categories/*.md` files to exist."
        )


# ---- Inputs -----------------------------------------------------------

st.subheader("Run a new analysis")

col_path, col_backend = st.columns([3, 1])
codebase_input = col_path.text_input(
    "Codebase path (absolute or repo-relative)",
    value=st.session_state.get("codebase_input", ""),
    placeholder="/Users/you/projects/my-driving-stack",
    key="codebase_input",
)
backend_options = ["anthropic", "claude_code"]
default_idx = backend_options.index(cfg.llm.default_backend) \
    if cfg.llm.default_backend in backend_options else 0
backend = col_backend.selectbox(
    "LLM backend",
    options=backend_options,
    index=default_idx,
    help=(
        "`anthropic` uses the API with a pre-walked file bundle; "
        "`claude_code` shells out to the `claude` CLI and may use Read/Glob "
        "tools to read more of the codebase. Both work; Claude Code can dig "
        "deeper if the bundle isn't enough."
    ),
)


col_a, col_b, col_c = st.columns([1, 1, 2])
preview = col_a.button(
    "Preview bundle", help="Walk the codebase and show what would be sent."
)
run = col_b.button("Run analysis", type="primary")
col_c.caption(
    "Reports save to `data/codebase_analyses/<repo>/<timestamp>.md`."
)


# ---- Resolve codebase path --------------------------------------------

def _resolve_codebase(raw: str) -> Path | None:
    if not raw.strip():
        return None
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = _REPO_ROOT / p
    return p.resolve()


cb_path = _resolve_codebase(codebase_input)


# ---- Preview branch ---------------------------------------------------

if preview:
    if not cb_path or not cb_path.exists() or not cb_path.is_dir():
        st.error(f"Path not found or not a directory: `{cb_path}`")
    else:
        try:
            bundle, files = bundle_codebase(cb_path)
            st.success(f"Bundle: {len(files)} file(s), {len(bundle):,} chars")
            for f in files:
                st.write(f"- `{f}`")
            with st.expander("Bundle preview (truncated)", expanded=False):
                st.code(bundle[:5_000] + ("\n…[truncated for preview]" if len(bundle) > 5_000 else ""))
        except Exception:
            st.error("Bundle walk crashed")
            st.code(traceback.format_exc())


# ---- Run branch -------------------------------------------------------

def _make_llm_client():
    """Lazy-build to defer the import + key-presence check until run time."""
    if backend == "anthropic":
        if not cfg.anthropic_api_key:
            st.error("ANTHROPIC_API_KEY not set in environment / .env")
            st.stop()
        from lib.llm.anthropic_client import AnthropicClient
        return AnthropicClient(
            api_key=cfg.anthropic_api_key,
            model=cfg.llm.anthropic.model,
            default_max_tokens=cfg.llm.anthropic.max_tokens,
            default_temperature=cfg.llm.anthropic.temperature,
        )
    from lib.llm.claude_code_client import ClaudeCodeClient
    return ClaudeCodeClient(binary=cfg.llm.claude_code.binary)


if run:
    if not cb_path or not cb_path.exists() or not cb_path.is_dir():
        st.error(f"Path not found or not a directory: `{cb_path}`")
    elif not SKILL_PATH.exists():
        st.error(f"Skill not found at `{SKILL_PATH}` — install the codebase-analyzer skill first.")
    else:
        repo_slug = cb_path.name or "repo"
        ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = ANALYSES_ROOT / repo_slug / f"{ts}.md"

        with st.status(
            f"Analyzing `{repo_slug}` with backend `{backend}` …",
            expanded=True,
        ) as status:
            try:
                st.write(f"- Walking codebase: `{cb_path}`")
                st.write(f"- Output:           `{out_path.relative_to(_REPO_ROOT)}`")
                llm = _make_llm_client()
                result = run_codebase_analysis(
                    codebase_path=cb_path,
                    output_path=out_path,
                    skill_md_path=SKILL_PATH,
                    wiki_root=WIKI_ROOT,
                    distilled_root=DISTILLED_ROOT,
                    llm=llm,
                )
                status.update(
                    label=(
                        f"Done — {len(result.files_bundled)} file(s) bundled, "
                        f"{result.bundle_size_chars:,} chars; report "
                        f"{len(result.report):,} chars."
                    ),
                    state="complete",
                )
                st.session_state["last_report_path"] = str(result.output_path)
            except Exception:
                status.update(label="Analysis crashed", state="error")
                st.code(traceback.format_exc())


# ---- Past runs ---------------------------------------------------------

st.divider()
st.subheader("Reports")

def _list_reports() -> list[Path]:
    if not ANALYSES_ROOT.exists():
        return []
    return sorted(ANALYSES_ROOT.rglob("*.md"), reverse=True)

reports = _list_reports()
if not reports:
    st.caption("No analyses yet. Run one above.")
else:
    options = [str(p.relative_to(_REPO_ROOT)) for p in reports]
    default = st.session_state.get("last_report_path")
    default_index = 0
    if default:
        try:
            default_index = next(
                i for i, p in enumerate(reports) if str(p) == default
            )
        except StopIteration:
            default_index = 0
    chosen_label = st.selectbox(
        "Pick a past run", options=options, index=default_index,
    )
    chosen = _REPO_ROOT / chosen_label
    if chosen.exists():
        st.caption(f"`{chosen_label}`")
        text = chosen.read_text()
        # Per the skill: split each "### N. <title>" proposal into its own
        # expander so the report stays scannable.
        st.markdown(text)
