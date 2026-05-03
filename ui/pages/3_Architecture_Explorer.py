"""Architecture Explorer — interactive faceted view of the corpus by inferred
architecture tag. Re-uses lib.indexing.from_distilled for parsing and tag
heuristics so the UI stays in sync with the deterministic generator.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import streamlit as st

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.indexing.from_distilled import (  # noqa: E402
    DistilledPaper,
    architecture_signature,
    discover_distilled,
    infer_arch_tags,
    _ARCH_PATTERNS,
)


st.set_page_config(
    page_title="Architecture Explorer",
    page_icon=":compass:",
    layout="wide",
)
st.title("Architecture Explorer")
st.caption(
    "Pick architecture tags + categories to filter the corpus. Each match expands "
    "to the full **Model Architecture** section from the source distillation."
)


# ---- Load corpus (cached) ----------------------------------------------

@st.cache_data(show_spinner=False)
def _load_corpus() -> tuple[list[dict], list[str], list[str]]:
    """Return (papers, all_tags, all_categories) using primitives that
    Streamlit can hash. Each paper is a dict snapshot of DistilledPaper +
    its inferred tags + signature so we don't re-walk on every interaction.
    """
    distilled_root = _REPO_ROOT / "doc" / "distilled"
    papers_raw: list[DistilledPaper] = discover_distilled(distilled_root)
    snapshots: list[dict] = []
    cats = set()
    for p in papers_raw:
        snapshots.append({
            "paper_id": p.paper_id,
            "title": p.title,
            "year": p.year,
            "venue": p.venue,
            "primary_category": p.primary_category,
            "url": p.url,
            "keywords": p.keywords,
            "one_line_summary": p.one_line_summary,
            "architecture": p.architecture,
            "signature": architecture_signature(p),
            "tags": infer_arch_tags(p),
            "path": str(p.path.relative_to(_REPO_ROOT)),
        })
        cats.add(p.primary_category)
    all_tags = list(_ARCH_PATTERNS.keys())
    return snapshots, all_tags, sorted(cats)


corpus, ALL_TAGS, ALL_CATEGORIES = _load_corpus()

if not corpus:
    st.info(
        f"No distilled MDs found under `doc/distilled/`. Run the "
        "`paper-distillation` skill on a paper first, or use the "
        "**Distillation Manager** page."
    )
    st.stop()

# Pre-compute tag counts across the whole corpus for the chip labels.
tag_counts = Counter()
for p in corpus:
    for t in p["tags"]:
        tag_counts[t] += 1


# ---- Sidebar controls --------------------------------------------------

st.sidebar.header("Filters")

selected_tags: list[str] = st.sidebar.multiselect(
    "Architecture tags",
    options=ALL_TAGS,
    format_func=lambda t: f"{t} ({tag_counts.get(t, 0)})",
    help=(
        "Heuristic clusters from keywords + the `## Model Architecture` body."
    ),
)

combine_mode: str = st.sidebar.radio(
    "Combine tags",
    options=["AND", "OR"],
    horizontal=True,
    index=0,
    help=(
        "AND = paper must carry every selected tag; OR = paper must carry "
        "any selected tag."
    ),
)

selected_cats: list[str] = st.sidebar.multiselect(
    "Primary category",
    options=ALL_CATEGORIES,
    default=[],
)

sort_by = st.sidebar.selectbox(
    "Sort by",
    options=["year (newest first)", "year (oldest first)",
            "paper_id (A→Z)", "title (A→Z)", "tag count (most-tagged first)"],
)

st.sidebar.divider()
st.sidebar.caption(
    f"Corpus: {len(corpus)} paper(s) across {len(ALL_CATEGORIES)} category(ies)."
)


# ---- Apply filters -----------------------------------------------------

def _matches(paper: dict) -> bool:
    if selected_cats and paper["primary_category"] not in selected_cats:
        return False
    if not selected_tags:
        return True
    paper_tags = set(paper["tags"])
    if combine_mode == "AND":
        return all(t in paper_tags for t in selected_tags)
    return any(t in paper_tags for t in selected_tags)


matches = [p for p in corpus if _matches(p)]

# Sort
if sort_by.startswith("year (newest"):
    matches.sort(key=lambda p: (-p["year"], p["paper_id"]))
elif sort_by.startswith("year (oldest"):
    matches.sort(key=lambda p: (p["year"], p["paper_id"]))
elif sort_by.startswith("paper_id"):
    matches.sort(key=lambda p: p["paper_id"])
elif sort_by.startswith("title"):
    matches.sort(key=lambda p: p["title"].lower())
elif sort_by.startswith("tag count"):
    matches.sort(key=lambda p: (-len(p["tags"]), p["paper_id"]))


# ---- Header summary ----------------------------------------------------

c1, c2, c3 = st.columns([1, 1, 2])
c1.metric("Matches", len(matches))
c2.metric("Tags selected", len(selected_tags))
c3.write("**Active filter:** " + (
    f"{combine_mode}({', '.join('`' + t + '`' for t in selected_tags) or '∅'})"
    + (f" • cat ∈ {selected_cats}" if selected_cats else "")
))

if not matches:
    st.info("No papers match the current filter. Loosen the tag combination "
            "(try OR), drop the category filter, or remove tags.")
    st.stop()


# ---- Result cards ------------------------------------------------------

for p in matches:
    arch_link = f"[{p['url']}]({p['url']})" if p["url"] else "—"
    title_line = f"**{p['paper_id']}** — {p['title']}"
    expander_label = (
        f"{p['paper_id']} · {p['primary_category']} · "
        f"{p['venue'] or 'arXiv'} {p['year']} · tags: "
        f"{', '.join(p['tags']) or '—'}"
    )
    with st.expander(expander_label, expanded=False):
        st.markdown(title_line)
        meta_cols = st.columns([2, 1, 1])
        meta_cols[0].markdown(f"**Summary:** {p['one_line_summary']}")
        meta_cols[1].markdown(f"**arXiv:** {arch_link}")
        meta_cols[2].markdown(f"**Distilled:** `{p['path']}`")
        st.markdown(f"**Keywords:** {', '.join(p['keywords'])}")
        st.markdown(f"**Architecture signature:** {p['signature']}")
        st.divider()
        st.markdown("### Model Architecture")
        st.markdown(p["architecture"] or "_(no architecture section in distillation)_")
