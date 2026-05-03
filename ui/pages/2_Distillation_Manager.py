"""Distillation Manager — diff PDFs vs distilled MDs, run API distillation,
clean up orphans."""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import streamlit as st

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.config import load_config  # noqa: E402
from lib.distillation.sync import (  # noqa: E402
    PaperEntry,
    check_sync,
    delete_orphan_distillations,
)


st.set_page_config(page_title="Distillation Manager", page_icon=":recycle:", layout="wide")
st.title("Distillation Manager")

cfg = load_config(_REPO_ROOT / "config")
papers_root = _REPO_ROOT / "doc" / "papers"
distilled_root = _REPO_ROOT / "doc" / "distilled"

# ---- Status ----------------------------------------------------------

status = check_sync(papers_root, distilled_root)
in_sync, missing, orphans = status.in_sync, status.missing, status.orphans

c1, c2, c3 = st.columns(3)
c1.metric("In sync", len(in_sync))
c2.metric("Missing distillation", len(missing))
c3.metric("Orphan distillation", len(orphans))


def _entry_row(e: PaperEntry) -> dict:
    return {
        "category": e.category,
        "stem": e.stem,
        "pdf": str(e.pdf_path.relative_to(_REPO_ROOT)) if e.pdf_path else "—",
        "distilled": str(e.md_path.relative_to(_REPO_ROOT)) if e.md_path else "—",
    }


# ---- Tabs ---------------------------------------------------------------

tab_missing, tab_orphans, tab_synced = st.tabs(
    [f"Missing ({len(missing)})",
     f"Orphans ({len(orphans)})",
     f"In sync ({len(in_sync)})"]
)

# ---- Missing tab: run distillation -------------------------------------

with tab_missing:
    st.markdown(
        "These PDFs do not yet have a distillation. "
        "Run distillation via the API (uses your `ANTHROPIC_API_KEY` and the LLM "
        "to produce a SKILL.md-format Markdown file). "
        "Each call costs API credits and takes ~30–60 s per paper."
    )
    if not missing:
        st.success("Nothing missing — every PDF has a matching distillation.")
    else:
        # Selection table
        keys = [(e.category, e.stem) for e in missing]
        select_all = st.checkbox("Select all missing", value=False)
        selected: list[PaperEntry] = []
        for e in missing:
            row_key = f"miss::{e.category}::{e.stem}"
            checked = st.checkbox(
                f"`{e.category}/{e.stem}.pdf`",
                value=select_all,
                key=row_key,
            )
            if checked:
                selected.append(e)

        backend_options = ["anthropic", "claude_code"]
        default_idx = backend_options.index(cfg.llm.default_backend) \
            if cfg.llm.default_backend in backend_options else 0
        backend = st.selectbox(
            "LLM backend",
            options=backend_options,
            index=default_idx,
            help="`anthropic` uses the API; `claude_code` shells out to the `claude` CLI.",
        )

        run = st.button(
            f"Run distillation on {len(selected)} paper(s)",
            type="primary",
            disabled=len(selected) == 0,
        )

        if run and selected:
            try:
                # Imported lazily so the page renders even if api_distill is
                # not yet importable for some reason.
                from lib.distillation.api_distill import distill_pdf_via_api  # noqa: E402
                from lib.llm.anthropic_client import AnthropicClient  # noqa: E402
                from lib.llm.claude_code_client import ClaudeCodeClient  # noqa: E402

                if backend == "anthropic":
                    if not cfg.anthropic_api_key:
                        st.error("ANTHROPIC_API_KEY not set in environment / .env")
                        st.stop()
                    llm = AnthropicClient(
                        api_key=cfg.anthropic_api_key,
                        model=cfg.llm.anthropic.model,
                        default_max_tokens=cfg.llm.anthropic.max_tokens,
                        default_temperature=cfg.llm.anthropic.temperature,
                    )
                else:
                    llm = ClaudeCodeClient(binary=cfg.llm.claude_code.binary)

                progress = st.progress(0.0, text=f"0 / {len(selected)} done")
                results_log = st.empty()
                rolling: list[str] = []
                for i, e in enumerate(selected, start=1):
                    out_path = distilled_root / e.category / f"{e.stem}.md"
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        with st.status(f"[{i}/{len(selected)}] {e.category}/{e.stem}",
                                       expanded=False) as s:
                            res = distill_pdf_via_api(
                                pdf_path=e.pdf_path,
                                output_path=out_path,
                                llm=llm,
                                max_full_md_chars=cfg.ingest.max_full_md_chars,
                            )
                            s.update(label=f"OK — {res.paper_id} ({res.word_count} words)",
                                     state="complete")
                            rolling.append(
                                f":white_check_mark: `{e.category}/{e.stem}` → "
                                f"`{res.paper_id}` ({res.primary_category}, {res.word_count} words)"
                            )
                    except Exception as exc:
                        rolling.append(
                            f":x: `{e.category}/{e.stem}` failed: `{exc}`"
                        )
                    progress.progress(i / len(selected),
                                      text=f"{i} / {len(selected)} done")
                    results_log.markdown("\n\n".join(rolling))

                st.success("Done. Re-running sync check on next page load.")
            except Exception:
                st.error("Distillation crashed before finishing.")
                st.code(traceback.format_exc())

# ---- Orphans tab: delete -----------------------------------------------

with tab_orphans:
    st.markdown(
        "These distilled MD files have no matching PDF "
        "(typically because the source PDF was removed). Deleting them keeps "
        "the wiki accurate."
    )
    if not orphans:
        st.success("No orphans.")
    else:
        select_all_o = st.checkbox("Select all orphans", value=False, key="select_all_o")
        selected_o: list[PaperEntry] = []
        for e in orphans:
            row_key = f"orph::{e.category}::{e.stem}"
            checked = st.checkbox(
                f"`{e.category}/{e.stem}.md`",
                value=select_all_o,
                key=row_key,
            )
            if checked:
                selected_o.append(e)

        confirm = st.text_input(
            "Type `delete` to confirm:",
            value="",
            placeholder="delete",
            key="orphan_delete_confirm",
        )
        delete = st.button(
            f"Delete {len(selected_o)} file(s)",
            type="primary",
            disabled=(len(selected_o) == 0 or confirm.strip().lower() != "delete"),
        )
        if delete and selected_o and confirm.strip().lower() == "delete":
            removed = delete_orphan_distillations(selected_o)
            st.success(f"Deleted {len(removed)} orphan distillation(s).")
            for p in removed:
                st.write(f"- `{p.relative_to(_REPO_ROOT)}`")

# ---- In-sync tab -------------------------------------------------------

with tab_synced:
    st.markdown("These are aligned: PDF and distillation both present.")
    if not in_sync:
        st.info("Nothing in sync yet.")
    else:
        st.dataframe(
            [_entry_row(e) for e in in_sync],
            use_container_width=True,
            hide_index=True,
        )

# ---- Footer: regenerate-wiki shortcut ----------------------------------

st.divider()
st.caption(
    "After distilling new papers or deleting orphans, regenerate the wiki "
    "with `python cli.py wiki-from-distilled` (no LLM call). The Wiki Browser "
    "page reads the resulting files."
)
