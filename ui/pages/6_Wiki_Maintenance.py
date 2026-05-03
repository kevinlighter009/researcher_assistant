"""Wiki Maintenance — regenerate the wiki from distillations, snapshot
the pending-distillations list, and surface the skill-driven editorial
prompt for manual application via Claude Code.
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

from lib.config import load_config  # noqa: E402
from lib.distillation.sync import check_sync  # noqa: E402
from lib.indexing.from_distilled import (  # noqa: E402
    discover_distilled,
    generate_wiki_from_distilled,
)


st.set_page_config(
    page_title="Wiki Maintenance",
    page_icon=":wrench:",
    layout="wide",
)
st.title("Wiki Maintenance")
st.caption(
    "Regenerate the wiki from distillations, snapshot pending-distillation "
    "coverage, and surface the editorial-layer prompt for manual application "
    "via Claude Code."
)

cfg = load_config(_REPO_ROOT / "config")
papers_root = _REPO_ROOT / "doc" / "papers"
distilled_root = _REPO_ROOT / "doc" / "distilled"
wiki_root = _REPO_ROOT / cfg.data_dir / "wiki" if not cfg.data_dir.is_absolute() \
    else cfg.data_dir / "wiki"
skill_path = _REPO_ROOT / "skills" / "wiki-generation" / "SKILL.md"
index_md = wiki_root / "index.md"
pending_md = wiki_root / "pending.md"


# ---- Current state ------------------------------------------------------

st.subheader("Current state")

papers = discover_distilled(distilled_root)
n_distilled = len(papers)

# Number of indexed papers (approximate from index.md row count)
if index_md.exists():
    n_indexed = sum(
        1 for line in index_md.read_text().splitlines()
        if line.startswith("| 20") or line.startswith("| 19")
    )
    last_regen = dt.datetime.fromtimestamp(
        index_md.stat().st_mtime
    ).strftime("%Y-%m-%d %H:%M:%S")
else:
    n_indexed = 0
    last_regen = "(never generated)"

status = check_sync(papers_root, distilled_root)

m_cols = st.columns(5)
m_cols[0].metric("Distillations", n_distilled)
m_cols[1].metric("Indexed in wiki", n_indexed)
m_cols[2].metric("Drift",
                 n_distilled - n_indexed,
                 delta_color="inverse" if n_distilled != n_indexed else "off")
m_cols[3].metric("Missing distillation", len(status.missing))
m_cols[4].metric("Orphan distillation", len(status.orphans))

st.caption(f"Wiki root: `{wiki_root.relative_to(_REPO_ROOT)}` · Last regen: {last_regen}")

drift = n_distilled != n_indexed
if drift:
    st.warning(
        f"The wiki is out of sync with `doc/distilled/` (drift "
        f"= {n_distilled - n_indexed}). Run **Regenerate wiki** below."
    )
elif n_distilled == 0:
    st.info(
        "No distilled MDs found. Run the **Distillation Manager** or the "
        "`paper-distillation` skill via Claude Code first."
    )
else:
    st.success(f"Wiki is up to date with the {n_distilled} distillation(s).")


# ---- Action: regenerate (deterministic, no LLM call) -------------------

st.divider()
st.subheader("Regenerate (deterministic, no LLM call)")
st.markdown(
    "Re-runs the deterministic generator: writes `index.md`, "
    "`categories/<cat>.md` (with full `## Model Architecture` sections), "
    "and `architectures.md`. **Overwrites existing auto-generated files**; "
    "preserves `taxonomy.md` and `pending.md`."
)

if st.button("Regenerate wiki", type="primary"):
    if not papers:
        st.error("No distillations found under `doc/distilled/`. Nothing to do.")
    else:
        try:
            with st.status("Regenerating…", expanded=True) as s:
                st.write(f"- Discovered **{len(papers)}** distillation(s)")
                out = generate_wiki_from_distilled(
                    papers, wiki_root, seed_taxonomy=cfg.seed_taxonomy,
                )
                st.write(f"- Wrote `{out.index_md.relative_to(_REPO_ROOT)}`")
                st.write(
                    f"- Wrote {len(out.categories)} category page(s) "
                    f"in `{(wiki_root / 'categories').relative_to(_REPO_ROOT)}/`"
                )
                st.write(
                    f"- Wrote `{out.architectures_md.relative_to(_REPO_ROOT)}`"
                )
                s.update(
                    label=f"Regenerated wiki for {out.paper_count} papers",
                    state="complete",
                )
            st.rerun()
        except Exception:
            st.error("Regeneration crashed.")
            st.code(traceback.format_exc())


# ---- Action: snapshot pending.md ---------------------------------------

st.divider()
st.subheader("Snapshot `pending.md`")
st.markdown(
    "Re-walks the corpus and writes `data/wiki/pending.md` listing PDFs "
    "with no matching distillation. Survives subsequent regenerations."
)

if st.button("Snapshot pending.md"):
    today = dt.date.today().isoformat()
    n_pending = len(status.missing)
    body = [
        "# Pending Distillations",
        "",
        "PDFs present under `doc/papers/<cat>/` with no matching "
        "distillation under `doc/distilled/<cat>/`. Surface these so "
        "coverage gaps are obvious; close them by running the "
        "`paper-distillation` skill (manual via Claude Code) or "
        "`python cli.py distill-run` (API).",
        "",
        f"({n_pending} pending — snapshot taken {today})",
        "",
        "| category | stem | source PDF |",
        "|----------|------|------------|",
    ]
    if status.missing:
        for e in status.missing:
            body.append(
                f"| {e.category} | {e.stem} | "
                f"`doc/papers/{e.category}/{e.stem}.pdf` |"
            )
    else:
        body.append("| _(none — all PDFs are distilled)_ | | |")
    pending_md.parent.mkdir(parents=True, exist_ok=True)
    pending_md.write_text("\n".join(body) + "\n")
    st.success(
        f"Wrote `{pending_md.relative_to(_REPO_ROOT)}` "
        f"({n_pending} pending)."
    )

if pending_md.exists():
    with st.expander("Preview pending.md", expanded=False):
        st.code(pending_md.read_text(), language="markdown")


# ---- Editorial-layer prompt --------------------------------------------

st.divider()
st.subheader("Editorial-layer refresh (manual)")
st.markdown(
    "The deterministic generator writes the routine bits. The editorial "
    "layer — `taxonomy.md`, per-category narrative intros, and the "
    "`architectures.md` cluster prose — is best produced by an LLM with "
    "judgment following `skills/wiki-generation/SKILL.md`. Copy the prompt "
    "below into Claude Code (the LLM will then read the SKILL.md and the "
    "current corpus state)."
)

if not skill_path.exists():
    st.error(f"Skill not found at `{skill_path.relative_to(_REPO_ROOT)}`. "
             "Install the wiki-generation skill first.")
else:
    prompt = (
        f"Apply the wiki-generation skill at `{skill_path.relative_to(_REPO_ROOT)}` "
        "in **Mode A — Full rebuild**, focusing on the editorial layer:\n\n"
        f"- Read all distillations under `{distilled_root.relative_to(_REPO_ROOT)}/`.\n"
        f"- Run the deterministic baseline first: `python cli.py wiki-from-distilled`. "
        "(I just did this; the auto bits are fresh.)\n"
        f"- Re-write `{wiki_root.relative_to(_REPO_ROOT)}/taxonomy.md` so every "
        "category in use has a 2-3-sentence description that captures what "
        "differentiates it from siblings.\n"
        f"- For each populated `{wiki_root.relative_to(_REPO_ROOT)}/categories/<cat>.md`, "
        "replace the placeholder intro line with a 2-sentence narrative that "
        "captures what the category covers and what its papers tend to focus on.\n"
        f"- For `{wiki_root.relative_to(_REPO_ROOT)}/architectures.md`, replace the "
        "auto-generated intro with a 2-paragraph editorial intro, and add a "
        "1-paragraph blurb above each `### \\`uses-<tag>\\`` heading describing "
        "what defines that cluster.\n"
        f"- Refresh `{wiki_root.relative_to(_REPO_ROOT)}/pending.md` from the "
        "current sync diff.\n"
        f"- Self-check per the skill's checklist; report what changed.\n\n"
        f"Current state: **{n_distilled}** distillation(s); "
        f"**{n_indexed}** indexed; "
        f"**{len(status.missing)}** missing; **{len(status.orphans)}** orphan."
    )
    st.code(prompt, language="markdown")
    st.caption(
        "Tip: in Claude Code, paste the prompt and the model will read "
        "the SKILL.md and apply it. The skill runs in your editor — the "
        "wiki files are gitignored, so changes stay local until you commit."
    )


# ---- Past wiki snapshots -----------------------------------------------

st.divider()
st.subheader("Files in `data/wiki/`")
if not wiki_root.exists():
    st.caption("(wiki not generated yet)")
else:
    rows = []
    for p in sorted(wiki_root.rglob("*.md")):
        stat = p.stat()
        rows.append({
            "path": str(p.relative_to(_REPO_ROOT)),
            "size_bytes": stat.st_size,
            "modified": dt.datetime.fromtimestamp(stat.st_mtime)
                          .strftime("%Y-%m-%d %H:%M:%S"),
        })
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.caption("(empty)")
