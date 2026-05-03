"""Wiki Browser — render the generated wiki Markdown files."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.config import load_config  # noqa: E402


st.set_page_config(page_title="Wiki Browser", page_icon=":open_book:", layout="wide")
st.title("Wiki Browser")

cfg = load_config(_REPO_ROOT / "config")
wiki_root = _REPO_ROOT / cfg.data_dir / "wiki" if not cfg.data_dir.is_absolute() \
    else cfg.data_dir / "wiki"
distilled_root = _REPO_ROOT / "doc" / "distilled"

# ---- Build file list ----------------------------------------------------

def _collect_files() -> dict[str, list[Path]]:
    """Group browsable files by section: wiki top-level, wiki categories,
    distilled per-paper. Sections are stable; keys are display labels."""
    groups: dict[str, list[Path]] = {
        "Wiki — top-level": [],
        "Wiki — categories": [],
        "Distillations": [],
    }
    if wiki_root.exists():
        for p in sorted(wiki_root.glob("*.md")):
            groups["Wiki — top-level"].append(p)
        cat_dir = wiki_root / "categories"
        if cat_dir.exists():
            for p in sorted(cat_dir.glob("*.md")):
                groups["Wiki — categories"].append(p)
    if distilled_root.exists():
        for p in sorted(distilled_root.rglob("*.md")):
            if p.name == "MANIFEST.md":
                continue
            groups["Distillations"].append(p)
    return groups


groups = _collect_files()
total = sum(len(v) for v in groups.values())

if total == 0:
    st.info(
        f"No Markdown files found under `{wiki_root.relative_to(_REPO_ROOT)}` or "
        f"`{distilled_root.relative_to(_REPO_ROOT)}`. Generate the wiki first via "
        "`python cli.py wiki-from-distilled` or the **Distillation Manager** page."
    )
    st.stop()

# ---- Sidebar nav --------------------------------------------------------

st.sidebar.header("Files")
search = st.sidebar.text_input("Filter", placeholder="search filename")

# Build flat label list for filtering, but keep grouping in display
selected_path: Path | None = None
for section, paths in groups.items():
    visible = [p for p in paths
               if not search or search.lower() in p.name.lower()
               or search.lower() in str(p).lower()]
    if not visible:
        continue
    st.sidebar.subheader(section)
    for p in visible:
        # Use a unique key per button to avoid collisions
        rel = p.relative_to(_REPO_ROOT)
        if st.sidebar.button(p.name, key=str(rel), use_container_width=True):
            st.session_state["wiki_browser_selected"] = str(p)

# Default-select the first wiki file on first load.
if "wiki_browser_selected" not in st.session_state:
    for section in ("Wiki — top-level", "Wiki — categories", "Distillations"):
        if groups.get(section):
            st.session_state["wiki_browser_selected"] = str(groups[section][0])
            break

selected_str = st.session_state.get("wiki_browser_selected")
if selected_str:
    selected_path = Path(selected_str)

# ---- Main pane ----------------------------------------------------------

if selected_path and selected_path.exists():
    rel = selected_path.relative_to(_REPO_ROOT)
    st.caption(f"`{rel}`")
    text = selected_path.read_text()
    st.markdown(text)
    with st.expander("Raw"):
        st.code(text, language="markdown")
else:
    st.info("Pick a file from the sidebar.")
