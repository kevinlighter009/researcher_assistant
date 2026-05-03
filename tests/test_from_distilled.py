"""Tests for lib.indexing.from_distilled."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from lib.indexing.from_distilled import (
    DistilledPaper,
    architecture_signature,
    discover_distilled,
    generate_wiki_from_distilled,
    infer_arch_tags,
    parse_distilled_md,
)


# Sample fixture content used across tests. Matches the SKILL.md schema.

VLA_MD = textwrap.dedent("""\
    ---
    paper_id: 2024-mockvla
    title: "MockVLA: Vision Language Driver"
    authors: [Alice]
    year: 2024
    venue: CVPR 2025
    arxiv_id: "2401.00001"
    url: https://arxiv.org/abs/2401.00001
    primary_category: vla
    secondary_categories: [e2e_planning]
    keywords: [vlm, mllm, qwen-vl, bev, slow-fast]
    one_line_summary: A VLM-based driver with slow-fast inference.
    distilled_at: 2026-05-02
    source_pdf: doc/papers/vla/mockvla-2024.pdf
    ---

    # MockVLA: Vision Language Driver

    ## Keywords
    - vlm, mllm, qwen-vl, bev, slow-fast

    ## TL;DR
    Mock TL;DR.

    ## Problem & Motivation
    Mock motivation.

    ## Innovation Points
    - **Slow-fast** — combines a slow VLM with a fast classical planner.

    ## Model Architecture
    - **Inputs:** 6 surround cameras at 1Hz.
    - **Backbone:** Qwen-VL 7B + ResNet-50 image encoder.
    - **BEV head:** deformable attention over 200x200 BEV queries.
    - **Output:** 6-second waypoint trajectory.
    - **Scale:** 7B params; trained on nuScenes.

    ## Benchmark Results
    nuScenes L2 0.30 m.

    ## Limitations & Open Questions
    Inference cost not addressed.
    """)


DIFF_MD = textwrap.dedent("""\
    ---
    paper_id: 2024-mockdiff
    title: "MockDiff: Truncated Diffusion Driver"
    authors: [Bob]
    year: 2024
    venue: CVPR 2025 (Highlight)
    arxiv_id: "2402.00002"
    url: https://arxiv.org/abs/2402.00002
    primary_category: diffusion_decoder
    secondary_categories: [e2e_planning]
    keywords: [diffusion-policy, anchored-gaussian, navsim]
    one_line_summary: Truncated diffusion policy with K-Means anchors.
    distilled_at: 2026-05-02
    source_pdf: doc/papers/diffusion_decoder/mockdiff-2024.pdf
    ---

    # MockDiff: Truncated Diffusion Driver

    ## Keywords
    - diffusion-policy, anchored-gaussian, navsim

    ## TL;DR
    Mock TL;DR.

    ## Problem & Motivation
    Mock motivation.

    ## Innovation Points
    - **Truncated diffusion** — denoising in 2 steps.

    ## Model Architecture
    - **Inputs:** 3 cameras + LiDAR.
    - **Backbone:** ResNet-34.
    - **Decoder:** 2-step DDIM truncated diffusion over K-Means trajectory anchors.
    - **Output:** 8-waypoint trajectory.

    ## Benchmark Results
    NAVSIM PDMS 88.1.

    ## Limitations & Open Questions
    Mock limits.
    """)


def write_md(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# ---------- parse_distilled_md ------------------------------------------


def test_parse_extracts_front_matter_and_sections(tmp_path):
    p = write_md(tmp_path / "x.md", VLA_MD)
    paper = parse_distilled_md(p)
    assert isinstance(paper, DistilledPaper)
    assert paper.paper_id == "2024-mockvla"
    assert paper.title.startswith("MockVLA")
    assert paper.year == 2024
    assert paper.venue == "CVPR 2025"
    assert paper.primary_category == "vla"
    assert paper.keywords == ["vlm", "mllm", "qwen-vl", "bev", "slow-fast"]
    assert "Qwen-VL" in paper.architecture
    assert "Backbone" in paper.architecture
    # All standard sections recognized
    for h in ("Keywords", "TL;DR", "Problem & Motivation",
              "Innovation Points", "Model Architecture",
              "Benchmark Results", "Limitations & Open Questions"):
        assert h in paper.sections, f"missing section: {h}"


def test_parse_raises_without_front_matter(tmp_path):
    p = write_md(tmp_path / "bad.md", "no front-matter here\n## Keywords\n- a\n")
    with pytest.raises(ValueError, match="missing YAML front-matter"):
        parse_distilled_md(p)


def test_parse_raises_when_front_matter_is_not_mapping(tmp_path):
    p = write_md(tmp_path / "bad.md", "---\n- list\n- not\n- mapping\n---\nbody\n")
    with pytest.raises(ValueError, match="not a mapping"):
        parse_distilled_md(p)


# ---------- discover_distilled ------------------------------------------


def test_discover_walks_recursively_and_skips_manifest(tmp_path):
    write_md(tmp_path / "vla" / "a.md", VLA_MD)
    write_md(tmp_path / "diffusion_decoder" / "b.md", DIFF_MD)
    write_md(tmp_path / "vla" / "MANIFEST.md", "# manifest, ignore me\n")
    write_md(tmp_path / "vla" / "no_fm.md", "raw notes, no front-matter\n")
    out = discover_distilled(tmp_path)
    paper_ids = sorted(p.paper_id for p in out)
    assert paper_ids == ["2024-mockdiff", "2024-mockvla"]


def test_discover_returns_empty_for_missing_root(tmp_path):
    assert discover_distilled(tmp_path / "does_not_exist") == []


# ---------- arch heuristics ---------------------------------------------


def test_infer_arch_tags_vla(tmp_path):
    paper = parse_distilled_md(write_md(tmp_path / "x.md", VLA_MD))
    tags = infer_arch_tags(paper)
    assert "uses-vlm-backbone" in tags
    assert "uses-bev-transformer" in tags
    assert "uses-classical-planner" in tags
    assert "uses-cnn-backbone" in tags  # ResNet-50 in arch text


def test_infer_arch_tags_diffusion(tmp_path):
    paper = parse_distilled_md(write_md(tmp_path / "x.md", DIFF_MD))
    tags = infer_arch_tags(paper)
    assert "uses-diffusion-head" in tags
    assert "uses-trajectory-anchors" in tags
    assert "uses-cnn-backbone" in tags  # ResNet-34


def test_architecture_signature_extracts_first_bullet(tmp_path):
    paper = parse_distilled_md(write_md(tmp_path / "x.md", VLA_MD))
    sig = architecture_signature(paper)
    # First bullet of the arch section
    assert sig.startswith("**Inputs:**")
    assert "6 surround cameras" in sig


# ---------- generate_wiki_from_distilled --------------------------------


def test_generator_writes_index_categories_and_arch_pages(tmp_path):
    wiki_root = tmp_path / "wiki"
    distilled_dir = tmp_path / "distilled"
    write_md(distilled_dir / "vla" / "a.md", VLA_MD)
    write_md(distilled_dir / "diffusion_decoder" / "b.md", DIFF_MD)
    papers = discover_distilled(distilled_dir)
    out = generate_wiki_from_distilled(
        papers, wiki_root,
        seed_taxonomy=["vla", "diffusion_decoder", "world_model", "misc"],
    )
    assert out.paper_count == 2
    # index.md has both papers
    idx = out.index_md.read_text()
    assert "| paper_id |" in idx
    assert "2024-mockvla" in idx
    assert "2024-mockdiff" in idx
    # categories: both populated cats and empty seed cats present
    cat_names = {p.name for p in out.categories}
    assert {"vla.md", "diffusion_decoder.md", "world_model.md", "misc.md"} <= cat_names
    # populated category embeds the architecture verbatim
    vla_page = (wiki_root / "categories" / "vla.md").read_text()
    assert "MockVLA" in vla_page
    assert "deformable attention" in vla_page
    assert "Qwen-VL" in vla_page
    assert "### Model Architecture" in vla_page
    # empty seed category still has the heading
    wm_page = (wiki_root / "categories" / "world_model.md").read_text()
    assert wm_page.startswith("# world_model")
    # architectures.md groups by tag and category
    arch_page = out.architectures_md.read_text()
    assert "## By inferred architecture tag" in arch_page
    assert "uses-vlm-backbone" in arch_page
    assert "uses-diffusion-head" in arch_page
    assert "## By primary category" in arch_page
    assert "2024-mockvla" in arch_page
    assert "2024-mockdiff" in arch_page


def test_generator_overwrites_existing_files(tmp_path):
    wiki_root = tmp_path / "wiki"
    wiki_root.mkdir()
    (wiki_root / "index.md").write_text("STALE")
    distilled_dir = tmp_path / "distilled"
    write_md(distilled_dir / "vla" / "a.md", VLA_MD)
    papers = discover_distilled(distilled_dir)
    out = generate_wiki_from_distilled(papers, wiki_root)
    text = out.index_md.read_text()
    assert "STALE" not in text
    assert "2024-mockvla" in text


def test_pipe_in_title_is_escaped(tmp_path):
    weird = VLA_MD.replace(
        'title: "MockVLA: Vision Language Driver"',
        'title: "MockVLA | Pipe in Title"',
    )
    distilled_dir = tmp_path / "distilled"
    write_md(distilled_dir / "vla" / "a.md", weird)
    papers = discover_distilled(distilled_dir)
    out = generate_wiki_from_distilled(papers, tmp_path / "wiki")
    idx = out.index_md.read_text()
    assert "MockVLA \\| Pipe in Title" in idx
