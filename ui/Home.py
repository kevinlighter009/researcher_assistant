"""Personal Library — Streamlit entrypoint.

Run with:
    streamlit run ui/Home.py

Multi-page app: this file is the landing page; further pages live under
``ui/pages/``. Streamlit auto-discovers them and renders a sidebar.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

# Make `lib` importable when streamlit is run from the repo root.
import sys
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.config import load_config  # noqa: E402
from lib.distillation.sync import check_sync  # noqa: E402


st.set_page_config(
    page_title="Personal Library",
    page_icon=":books:",
    layout="wide",
)

st.title("Personal Library")
st.caption(
    "An LLM-maintained wiki for autonomous-driving research papers. "
    "Inspired by Karpathy's *LLM wiki* idea."
)

cfg = load_config(_REPO_ROOT / "config")
papers_root = _REPO_ROOT / "doc" / "papers"
distilled_root = _REPO_ROOT / "doc" / "distilled"
wiki_root = _REPO_ROOT / cfg.data_dir / "wiki" if not cfg.data_dir.is_absolute() \
    else cfg.data_dir / "wiki"

# ---- Status overview ----------------------------------------------------

status = check_sync(papers_root, distilled_root)

col1, col2, col3, col4 = st.columns(4)
col1.metric("PDFs", sum(1 for e in status.entries if e.has_pdf))
col2.metric("Distillations", sum(1 for e in status.entries if e.has_md))
col3.metric("In sync", len(status.in_sync))
col4.metric("Missing distillation", len(status.missing))

if status.orphans:
    st.warning(
        f"{len(status.orphans)} orphan distillation(s) — distilled MD with no "
        "matching PDF. See **Distillation Manager**."
    )

# ---- Wiki status --------------------------------------------------------

st.subheader("Wiki status")
index_md = wiki_root / "index.md"
if index_md.exists():
    n_rows = max(0, sum(1 for _ in index_md.read_text().splitlines()
                        if _.startswith("| 20")))
    st.write(f":white_check_mark: Wiki present at `{wiki_root.relative_to(_REPO_ROOT)}` "
             f"with **{n_rows}** indexed paper(s).")
else:
    st.info(
        f"Wiki not generated yet. Run `python cli.py wiki-from-distilled` "
        f"or use the Distillation Manager."
    )

# ---- Navigation hint ----------------------------------------------------

st.subheader("Pages")
st.markdown(
    """
- **Wiki Browser** — browse the generated `index.md`, `architectures.md`, and
  `categories/<cat>.md` files.
- **Distillation Manager** — see which PDFs are missing a distillation, run
  API-driven distillation for missing ones, and clean up orphans.

The manual Claude Code distillation flow (using `skills/paper-distillation/SKILL.md`)
remains available outside the UI.
""")

st.divider()
st.caption(
    "Repo: `~/Documents/code/llm_project/personal_library` "
    "• See `docs/superpowers/specs/` and `docs/superpowers/plans/` for design history."
)
