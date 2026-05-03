"""Compare — side-by-side architecture and benchmark comparison of 2-3
papers from the corpus."""
from __future__ import annotations

import re
import sys
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
)


st.set_page_config(
    page_title="Compare",
    page_icon=":left_right_arrow:",
    layout="wide",
)
st.title("Compare")
st.caption(
    "Pick 2 or 3 distilled papers and view their architecture, benchmark, and "
    "metadata in adjacent columns. Optional: highlight keywords shared across "
    "the selected papers."
)


# ---- Load corpus (cached) -----------------------------------------------

@st.cache_data(show_spinner=False)
def _load_corpus() -> list[dict]:
    distilled_root = _REPO_ROOT / "doc" / "distilled"
    out: list[dict] = []
    for p in discover_distilled(distilled_root):
        out.append({
            "paper_id": p.paper_id,
            "title": p.title,
            "year": p.year,
            "venue": p.venue,
            "url": p.url,
            "primary_category": p.primary_category,
            "secondary_categories": p.front_matter.get("secondary_categories", []),
            "keywords": p.keywords,
            "tags": infer_arch_tags(p),
            "signature": architecture_signature(p),
            "one_line_summary": p.one_line_summary,
            "tldr": p.sections.get("TL;DR", ""),
            "architecture": p.architecture,
            "benchmarks": p.sections.get("Benchmark Results", ""),
            "innovation": p.sections.get("Innovation Points", ""),
            "limitations": p.sections.get("Limitations & Open Questions", ""),
        })
    out.sort(key=lambda x: (x["primary_category"], x["paper_id"]))
    return out


corpus = _load_corpus()
if not corpus:
    st.info(
        "No distilled papers found under `doc/distilled/`. Distill some "
        "first via the `paper-distillation` skill or the **Distillation "
        "Manager** page."
    )
    st.stop()


by_id: dict[str, dict] = {p["paper_id"]: p for p in corpus}


# ---- Selection ---------------------------------------------------------

def _label(p: dict) -> str:
    return f"{p['paper_id']}  ·  {p['primary_category']}  ·  {p['title']}"


labels = [_label(p) for p in corpus]
label_to_id = {_label(p): p["paper_id"] for p in corpus}

c_select, c_opts = st.columns([3, 1])
selected_labels: list[str] = c_select.multiselect(
    "Pick 2 or 3 papers",
    options=labels,
    max_selections=3,
    placeholder="search / pick papers",
)
highlight = c_opts.checkbox(
    "Highlight shared keywords",
    value=True,
    help="Bold keywords that appear in every selected paper's keyword list.",
)

if len(selected_labels) < 2:
    st.info("Pick at least 2 papers to compare.")
    st.stop()
if len(selected_labels) > 3:
    st.warning("More than 3 papers selected — capping at the first 3 for layout.")
    selected_labels = selected_labels[:3]

papers = [by_id[label_to_id[lbl]] for lbl in selected_labels]
n = len(papers)


# ---- Compute shared keywords / shared tags -----------------------------

shared_keywords: set[str] = set.intersection(
    *(set(p["keywords"]) for p in papers)
) if papers else set()
shared_tags: set[str] = set.intersection(
    *(set(p["tags"]) for p in papers)
) if papers else set()


def _highlight_keywords(text: str, keywords: set[str]) -> str:
    """Bold each keyword (case-insensitive whole-token match) in ``text``,
    returning Markdown. Tokens like `diffusion-policy` are matched as
    written (kebab-case stays grouped)."""
    if not keywords or not text:
        return text
    # Sort longest first so substrings don't pre-empt longer matches
    pat_alts = [re.escape(k) for k in sorted(keywords, key=len, reverse=True)]
    pattern = re.compile(
        r"(?<![A-Za-z0-9_-])(" + "|".join(pat_alts) + r")(?![A-Za-z0-9_-])",
        re.IGNORECASE,
    )

    def _bold(m: re.Match) -> str:
        return f"**{m.group(0)}**"

    return pattern.sub(_bold, text)


def _format_keyword_list(p: dict) -> str:
    if not p["keywords"]:
        return "—"
    parts = []
    for k in p["keywords"]:
        if highlight and k in shared_keywords:
            parts.append(f"**`{k}`**")
        else:
            parts.append(f"`{k}`")
    return ", ".join(parts)


def _format_tag_list(p: dict) -> str:
    if not p["tags"]:
        return "—"
    parts = []
    for t in p["tags"]:
        if highlight and t in shared_tags:
            parts.append(f"**`{t}`**")
        else:
            parts.append(f"`{t}`")
    return ", ".join(parts)


# ---- Header summary ----------------------------------------------------

st.markdown(
    f"**Comparing {n} papers.** "
    + (
        f"Shared keywords (in all): "
        + (
            ", ".join(f"`{k}`" for k in sorted(shared_keywords))
            if shared_keywords else "*none*"
        )
    )
)
st.markdown(
    "Shared architecture tags (in all): "
    + (
        ", ".join(f"`{t}`" for t in sorted(shared_tags))
        if shared_tags else "*none*"
    )
)
st.divider()


# ---- Side-by-side columns ----------------------------------------------

cols = st.columns(n)

for col, p in zip(cols, papers):
    with col:
        st.markdown(f"### {p['paper_id']}")
        st.markdown(f"**{p['title']}**")
        st.caption(f"{p['venue'] or 'arXiv'} · {p['year']} · {p['primary_category']}")
        if p["url"]:
            st.markdown(f"[arXiv]({p['url']})")
        st.markdown(f"**Summary:** {p['one_line_summary']}")
        st.markdown(f"**Keywords:** {_format_keyword_list(p)}")
        st.markdown(f"**Arch tags:** {_format_tag_list(p)}")
        st.markdown(f"**Architecture signature:** {p['signature']}")

        st.divider()

        # TL;DR
        if p["tldr"]:
            with st.expander("TL;DR", expanded=True):
                body = p["tldr"]
                if highlight and shared_keywords:
                    body = _highlight_keywords(body, shared_keywords)
                st.markdown(body)

        # Innovation
        if p["innovation"]:
            with st.expander("Innovation Points", expanded=False):
                body = p["innovation"]
                if highlight and shared_keywords:
                    body = _highlight_keywords(body, shared_keywords)
                st.markdown(body)

        # Architecture (always expanded — this is the comparison's value)
        with st.expander("Model Architecture", expanded=True):
            body = p["architecture"] or "_(no architecture section)_"
            if highlight and shared_keywords:
                body = _highlight_keywords(body, shared_keywords)
            st.markdown(body)

        # Benchmarks
        with st.expander("Benchmark Results", expanded=True):
            body = p["benchmarks"] or "_(no benchmark section)_"
            if highlight and shared_keywords:
                body = _highlight_keywords(body, shared_keywords)
            st.markdown(body)

        # Limitations
        if p["limitations"]:
            with st.expander("Limitations & Open Questions", expanded=False):
                st.markdown(p["limitations"])
