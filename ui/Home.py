"""Personal Library — Streamlit entrypoint.

Run with:
    streamlit run ui/Home.py

Multi-page app: this file is the landing page; further pages live under
``ui/pages/``. Streamlit auto-discovers them and renders a sidebar.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st

# Make `lib` importable when streamlit is run from the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.config import load_config  # noqa: E402
from lib.distillation.sync import check_sync  # noqa: E402
from lib.indexing.from_distilled import (  # noqa: E402
    discover_distilled,
    infer_arch_tags,
    _ARCH_PATTERNS,
)


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

# ---- Sync status overview -----------------------------------------------

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
        f"or use the **Wiki Maintenance** page."
    )


# ---- Stats dashboard ----------------------------------------------------

@st.cache_data(show_spinner=False)
def _load_corpus_stats() -> dict:
    """Walk doc/distilled and produce all the data-frames the dashboard
    needs. Cached so the page doesn't re-walk on every interaction."""
    papers = discover_distilled(distilled_root)
    if not papers:
        return {"empty": True}

    rows = []
    tag_pairs: list[tuple[str, str]] = []  # (paper_id, tag)
    tag_counter: Counter = Counter()
    for p in papers:
        tags = infer_arch_tags(p)
        rows.append({
            "paper_id": p.paper_id,
            "year": p.year,
            "category": p.primary_category,
            "venue": p.venue or "arXiv",
            "tag_count": len(tags),
            "title": p.title,
        })
        for t in tags:
            tag_pairs.append((p.paper_id, t))
            tag_counter[t] += 1

    df = pd.DataFrame(rows)
    df_tags = pd.DataFrame(tag_pairs, columns=["paper_id", "tag"])

    # Per-year counts (sorted ascending)
    by_year = df.groupby("year").size().rename("papers").to_frame()
    by_year = by_year.sort_index()

    # Per-category
    by_cat = (df.groupby("category").size().rename("papers")
              .sort_values(ascending=False).to_frame())

    # Per-tag (canonical order from _ARCH_PATTERNS)
    canonical_tags = list(_ARCH_PATTERNS.keys())
    tag_series = pd.Series(
        {t: tag_counter.get(t, 0) for t in canonical_tags},
        name="papers",
    )
    by_tag = tag_series[tag_series > 0].to_frame()

    # Coverage matrix: year x category
    yc_matrix = (
        df.pivot_table(index="year", columns="category",
                       aggfunc="size", fill_value=0)
        .sort_index()
    )

    # Coverage matrix: tag x category (papers can carry multiple tags)
    tagged = df_tags.merge(df[["paper_id", "category"]], on="paper_id")
    tc_matrix = (
        tagged.pivot_table(index="tag", columns="category",
                           aggfunc="size", fill_value=0)
    )
    # Reorder rows to canonical tag order, drop empty rows
    tc_matrix = tc_matrix.reindex(
        [t for t in canonical_tags if t in tc_matrix.index]
    )

    # Top-tagged papers (most architecture tags = most architecturally rich)
    top_tagged = (
        df.sort_values(["tag_count", "year"], ascending=[False, False])
        .head(8)[["paper_id", "title", "year", "category", "tag_count"]]
        .reset_index(drop=True)
    )

    # Headline numbers
    summary = {
        "total_papers": len(papers),
        "year_min": int(df["year"].min()),
        "year_max": int(df["year"].max()),
        "n_categories": int(df["category"].nunique()),
        "n_tags_active": int((tag_series > 0).sum()),
        "n_tags_canonical": len(canonical_tags),
    }

    return {
        "empty": False,
        "summary": summary,
        "by_year": by_year,
        "by_cat": by_cat,
        "by_tag": by_tag,
        "yc_matrix": yc_matrix,
        "tc_matrix": tc_matrix,
        "top_tagged": top_tagged,
    }


st.subheader("Corpus stats")

stats = _load_corpus_stats()
if stats.get("empty"):
    st.info(
        "No distilled papers found. Once the corpus has a few distillations "
        "the dashboard will populate here."
    )
else:
    s = stats["summary"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total papers", s["total_papers"])
    m2.metric("Year span", f"{s['year_min']}–{s['year_max']}")
    m3.metric("Categories in use", s["n_categories"])
    m4.metric("Active arch tags",
              f"{s['n_tags_active']}/{s['n_tags_canonical']}")

    # ---- Three bar charts -------------------------------------------

    chart_cols = st.columns(3)
    with chart_cols[0]:
        st.markdown("**Papers per year**")
        st.bar_chart(stats["by_year"], height=220)
    with chart_cols[1]:
        st.markdown("**Papers per category**")
        st.bar_chart(stats["by_cat"], height=220)
    with chart_cols[2]:
        st.markdown("**Papers per architecture tag** (non-exclusive)")
        st.bar_chart(stats["by_tag"], height=220)

    # ---- Coverage matrices ------------------------------------------

    st.markdown("**Coverage matrix — year × category**")
    st.caption(
        "Where the corpus is thick / thin across publication year and "
        "primary category. Surfaces gaps to prioritize."
    )
    yc = stats["yc_matrix"]
    st.dataframe(
        yc.style.background_gradient(cmap="Blues", axis=None),
        use_container_width=True,
    )

    st.markdown("**Coverage matrix — architecture tag × category**")
    st.caption(
        "Tags are non-exclusive — a paper can appear in multiple rows. "
        "Reveals which architectural patterns dominate which research areas."
    )
    tc = stats["tc_matrix"]
    st.dataframe(
        tc.style.background_gradient(cmap="Blues", axis=None),
        use_container_width=True,
    )

    # ---- Top-tagged papers ------------------------------------------

    st.markdown("**Most architecturally rich papers** (by tag count)")
    st.caption(
        "Papers carrying the most architecture tags — typically those that "
        "compose multiple paradigms (e.g. BEV transformer + diffusion head + "
        "trajectory anchors)."
    )
    st.dataframe(
        stats["top_tagged"], use_container_width=True, hide_index=True,
    )


# ---- Pages directory ----------------------------------------------------

st.divider()
st.subheader("Pages")
st.markdown(
    """
- **Wiki Browser** — markdown viewer for the wiki + distilled MDs; BM25 content
  search; optional Notes mode for personal annotations.
- **Distillation Manager** — see which PDFs are missing a distillation, run
  API-driven distillation, clean up orphans.
- **Architecture Explorer** — faceted view by inferred architecture tag with
  AND/OR combine and sort options; expand a card to see the full architecture
  section.
- **Codebase Analyzer** — point at a target codebase to get wiki-grounded
  upgrade proposals (backed by `skills/codebase-analyzer/SKILL.md`).
- **Compare** — side-by-side architecture / benchmark comparison of 2-3 papers
  with shared-keyword highlighting.
- **Wiki Maintenance** — regenerate the wiki from distillations, snapshot the
  pending-distillations list, and surface skill-driven editorial-layer prompts.

The manual Claude Code distillation flow (using `skills/paper-distillation/SKILL.md`)
and the manual wiki-generation skill (using `skills/wiki-generation/SKILL.md`)
remain available outside the UI.
""")

st.divider()
st.caption(
    "Repo: `~/Documents/code/llm_project/personal_library` "
    "• See `docs/superpowers/specs/` and `docs/superpowers/plans/` for design history."
)
