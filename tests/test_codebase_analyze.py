"""Tests for lib.codebase.analyze."""
from __future__ import annotations

from pathlib import Path

import pytest

from lib.codebase.analyze import (
    CodebaseAnalysis,
    bundle_codebase,
    run_codebase_analysis,
)
from lib.llm.fake import FakeLLMClient


# ---------- fixture: a tiny synthetic codebase ----------


def make_fake_codebase(root: Path) -> Path:
    """Create a small synthetic codebase covering the file types the bundler
    actively reads (README, setup, model file, train, data, forward/eval).
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# My Driving Stack\n\nA tiny test repo.\n")
    (root / "pyproject.toml").write_text("[project]\nname = 'mds'\n")
    (root / "models").mkdir(parents=True, exist_ok=True)
    (root / "models" / "model.py").write_text(
        "import torch.nn as nn\n"
        "class DriverModel(nn.Module):\n"
        "    def __init__(self):\n"
        "        super().__init__()\n"
        "        # ResNet-50 backbone\n"
        "        self.backbone = ResNet50()\n"
        "    def forward(self, x):\n"
        "        return self.backbone(x)\n"
    )
    (root / "train.py").write_text(
        "from models.model import DriverModel\n"
        "model = DriverModel()\n"
        "optim = torch.optim.AdamW(model.parameters())\n"
        "loss = nn.MSELoss()\n"
    )
    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / "data" / "loader.py").write_text(
        "from torch.utils.data import DataLoader\n"
        "# nuScenes loader stub\n"
    )
    (root / "inference.py").write_text("# single-pass inference stub\n")
    (root / "node_modules").mkdir(parents=True, exist_ok=True)  # blocklist
    (root / "node_modules" / "junk.js").write_text("should be ignored")
    return root


# ---------- bundle_codebase ----------


def test_bundle_includes_readme_setup_layout_and_strategic_files(tmp_path):
    root = make_fake_codebase(tmp_path / "repo")
    bundle, files = bundle_codebase(root)
    # README + setup
    assert "README.md" in files
    assert "pyproject.toml" in files
    # Layout listing present
    assert "### Top-level layout" in bundle
    # Strategic source files
    assert any("model.py" in f for f in files)
    assert "train.py" in files
    assert any("loader.py" in f for f in files)
    assert "inference.py" in files
    # Backbone hint visible in bundle (so the LLM sees architecture context)
    assert "ResNet50" in bundle
    # Blocklisted dir excluded
    assert not any("node_modules" in f for f in files)


def test_bundle_truncates_per_file(tmp_path):
    root = make_fake_codebase(tmp_path / "repo")
    big = "x" * 50_000
    (root / "models" / "model.py").write_text(big)
    bundle, files = bundle_codebase(root, max_per_file_chars=1000)
    assert "[truncated]" in bundle
    # Truncation cap respected
    assert bundle.count("x" * 1000) <= 2


def test_bundle_respects_total_char_budget(tmp_path):
    root = make_fake_codebase(tmp_path / "repo")
    # Tiny budget — only the first few files (README) should fit
    bundle, files = bundle_codebase(
        root, max_per_file_chars=1000, total_char_budget=200,
    )
    # Layout block is appended unconditionally; that's fine. We just want to
    # confirm that "many files" weren't bundled when the budget was tiny.
    assert len(files) <= 3


def test_bundle_missing_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        bundle_codebase(tmp_path / "does_not_exist")


# ---------- run_codebase_analysis ----------


SAMPLE_REPORT = (
    "# Upgrade Proposals: my-driving-stack\n\n"
    "**Analyzed:** 2026-05-03\n"
    "**Codebase root:** /tmp/repo\n\n"
    "## Codebase Summary\nA mock driving stack.\n\n"
    "## Identified Methods\n| Axis | Current | Source |\n"
    "|---|---|---|\n| Backbone | ResNet-50 | models/model.py:6 |\n\n"
    "## Wiki Tag Map\nTags present: `uses-cnn-backbone`.\n\n"
    "## Proposed Upgrades\n### 1. Try diffusion head\n"
    "**Wiki precedent:** `2024-diffusiondrive`\n"
)


def test_run_writes_report_and_includes_bundle_in_prompt(tmp_path):
    root = make_fake_codebase(tmp_path / "repo")
    skill = tmp_path / "SKILL.md"
    skill.write_text("---\nname: codebase-analyzer\n---\n# fake skill\n")
    out_path = tmp_path / "UPGRADE_PROPOSALS.md"
    fake = FakeLLMClient(
        responses=[f"<result>{SAMPLE_REPORT}</result>"]
    )
    result = run_codebase_analysis(
        codebase_path=root,
        output_path=out_path,
        skill_md_path=skill,
        wiki_root=tmp_path / "wiki",
        distilled_root=tmp_path / "distilled",
        llm=fake,
    )
    assert isinstance(result, CodebaseAnalysis)
    assert result.output_path == out_path
    assert out_path.exists()
    # _strip_result_tags trims surrounding whitespace; compare stripped forms.
    assert out_path.read_text() == SAMPLE_REPORT.strip()
    assert "ResNet-50" in result.report  # extracted from <result>...</result>
    # The bundle was actually included in the user prompt
    user_prompt = fake.calls[0].user
    assert "ResNet50" in user_prompt
    assert "README.md" in user_prompt
    # Skill text was passed as system
    assert "name: codebase-analyzer" in fake.calls[0].system
    # Bundle metadata returned
    assert result.bundle_size_chars > 0
    assert "README.md" in result.files_bundled


def test_run_handles_no_result_tags(tmp_path):
    """If the LLM forgets to wrap its output in <result>...</result>, we
    still write the full text (after strip)."""
    root = make_fake_codebase(tmp_path / "repo")
    skill = tmp_path / "SKILL.md"
    skill.write_text("# skill\n")
    out_path = tmp_path / "report.md"
    fake = FakeLLMClient(responses=["raw report content with no tags"])
    result = run_codebase_analysis(
        codebase_path=root, output_path=out_path,
        skill_md_path=skill,
        wiki_root=tmp_path, distilled_root=tmp_path, llm=fake,
    )
    assert result.report == "raw report content with no tags"
    assert out_path.read_text() == "raw report content with no tags"


def test_run_missing_skill_raises(tmp_path):
    root = make_fake_codebase(tmp_path / "repo")
    fake = FakeLLMClient(responses=["x"])
    with pytest.raises(FileNotFoundError, match="skill not found"):
        run_codebase_analysis(
            codebase_path=root,
            output_path=tmp_path / "out.md",
            skill_md_path=tmp_path / "missing-skill.md",
            wiki_root=tmp_path, distilled_root=tmp_path, llm=fake,
        )
