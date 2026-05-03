"""Wiki Browser — render the generated wiki Markdown files."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.config import load_config  # noqa: E402
from lib.search import SearchIndex  # noqa: E402


st.set_page_config(page_title="Wiki Browser", page_icon=":open_book:", layout="wide")
st.title("Wiki Browser")

cfg = load_config(_REPO_ROOT / "config")
wiki_root = _REPO_ROOT / cfg.data_dir / "wiki" if not cfg.data_dir.is_absolute() \
    else cfg.data_dir / "wiki"
distilled_root = _REPO_ROOT / "doc" / "distilled"
_INDEX_PATH = _REPO_ROOT / "data" / ".search_index.json"

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


def _build_index() -> SearchIndex:
    roots = [wiki_root, distilled_root]
    idx = SearchIndex.build(roots, repo_root=_REPO_ROOT)
    idx.save(_INDEX_PATH)
    return idx


@st.cache_resource
def _get_or_build_index() -> SearchIndex:
    if _INDEX_PATH.exists():
        try:
            return SearchIndex.load(_INDEX_PATH)
        except (OSError, ValueError):
            pass
    return _build_index()


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
search = st.sidebar.text_input(
    "Search",
    placeholder="content search (>=2 chars) or filename filter",
)
if st.sidebar.button("Reindex", use_container_width=True):
    _get_or_build_index.clear()
    _build_index()
    st.sidebar.success("search index rebuilt")

selected_path: Path | None = None

if search and len(search.strip()) >= 2:
    # ---- Search mode: ranked content hits -------------------------------
    idx = _get_or_build_index()
    hits = idx.search(search.strip(), k=15)
    st.sidebar.subheader(f"Top {len(hits)} results")
    if not hits:
        st.sidebar.caption("no matches")
    for i, h in enumerate(hits):
        abs_path = _REPO_ROOT / h.file_path
        basename = Path(h.file_path).name
        heading = h.heading or "(preamble)"
        if len(heading) > 60:
            heading = heading[:57] + "..."
        label = f"{basename} - {heading}"
        if st.sidebar.button(
            label, key=f"search_hit_{i}", use_container_width=True,
        ):
            st.session_state["wiki_browser_selected"] = str(abs_path)
        snippet = h.snippet
        if len(snippet) > 220:
            snippet = snippet[:220] + "..."
        st.sidebar.caption(snippet)
else:
    # ---- Browse mode: grouped file list ---------------------------------
    for section, paths in groups.items():
        visible = [p for p in paths
                   if not search or search.lower() in p.name.lower()
                   or search.lower() in str(p).lower()]
        if not visible:
            continue
        st.sidebar.subheader(section)
        for p in visible:
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
