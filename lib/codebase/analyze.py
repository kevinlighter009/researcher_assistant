"""Codebase analyzer runner.

Implements the workflow described by ``skills/codebase-analyzer/SKILL.md``:
walk a target codebase selectively, bundle the strategic files into context,
hand them to an ``LLMClient`` along with the SKILL.md guidance and a wiki
pointer, capture the resulting Markdown report, and persist it.

Two operating modes:

- **Bundled** (default, works with any ``LLMClient`` including
  ``AnthropicClient``): we walk the codebase ourselves and embed the
  selected file contents in the user prompt. The LLM has no tool access; it
  reasons over the bundled bytes only.
- **Tool-using** (``ClaudeCodeClient``): we still bundle a starter set of
  files, but the LLM can use Read/Glob/Bash tools to read more if needed.
  No special code path here — the same prompt works; we just trust the
  client to use tools when available.

The runner does not edit the target codebase. It writes the report to a
caller-specified output path (by default ``data/codebase_analyses/<repo>/<ts>.md``).
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

from lib.llm.base import LLMClient


# --- File-selection rules (mirror the SKILL.md heuristics) ----------------

_TOP_LEVEL_DOC_PATTERNS = ("README*", "*.md", "*.rst")
_SETUP_FILES = (
    "pyproject.toml", "setup.py", "setup.cfg",
    "requirements.txt", "requirements-*.txt",
    "environment.yml", "package.json", "Cargo.toml",
    "go.mod",
)
_MODEL_GLOBS = (
    "**/model.py", "**/models.py", "**/model*.py", "**/network.py",
    "**/networks/*.py", "**/architecture.py", "**/architectures/*.py",
    "**/policy.py", "**/policies/*.py", "**/heads/*.py", "**/decoders/*.py",
    "**/encoders/*.py", "**/backbone.py",
)
_TRAIN_GLOBS = (
    "**/train.py", "**/main.py", "**/trainer.py", "**/pl_module.py",
    "**/run.py",
)
_DATA_GLOBS = (
    "**/dataset.py", "**/datasets/*.py", "**/data_loader.py",
    "**/loader.py", "**/data/*.py",
)
_FORWARD_GLOBS = (
    "**/forward.py", "**/inference.py", "**/eval.py", "**/evaluate.py",
)
_DIR_BLOCKLIST = {
    "node_modules", ".git", ".venv", "venv", "__pycache__",
    ".pytest_cache", "build", "dist", "target", ".tox", ".idea",
    ".mypy_cache", ".ruff_cache", "site-packages",
}


# --- Public API ----------------------------------------------------------


@dataclass
class CodebaseAnalysis:
    """Result of one analysis run."""

    output_path: Path
    report: str
    bundle_size_chars: int
    files_bundled: list[str]


def bundle_codebase(
    codebase_path: Path,
    *,
    max_per_file_chars: int = 4000,
    total_char_budget: int = 200_000,
) -> tuple[str, list[str]]:
    """Walk ``codebase_path`` and produce a single Markdown bundle of the
    strategic files plus a top-level layout listing.

    Returns ``(bundle_text, list_of_relative_paths_included)``. Files are
    truncated to ``max_per_file_chars`` each; total bundle is capped at
    ``total_char_budget`` (cap is approximate — the last file may overshoot
    by up to one max_per_file_chars).
    """
    codebase_path = Path(codebase_path).resolve()
    if not codebase_path.exists() or not codebase_path.is_dir():
        raise FileNotFoundError(codebase_path)

    parts: list[str] = []
    files_added: list[str] = []
    total = 0

    def _add(p: Path, label: str) -> bool:
        nonlocal total
        if total >= total_char_budget:
            return False
        try:
            text = p.read_text(errors="replace")
        except OSError:
            return False
        rel = p.relative_to(codebase_path).as_posix()
        if rel in files_added:
            return True  # already added
        if len(text) > max_per_file_chars:
            text = text[:max_per_file_chars] + "\n... [truncated]\n"
        block = f"\n\n### {label}: `{rel}`\n```\n{text}\n```\n"
        parts.append(block)
        files_added.append(rel)
        total += len(block)
        return True

    # 1) README + top-level Markdown / RST docs
    for pat in _TOP_LEVEL_DOC_PATTERNS:
        for p in sorted(codebase_path.glob(pat))[:3]:
            if p.is_file():
                _add(p, "Doc")

    # 2) Setup / dependency files
    for name in _SETUP_FILES:
        for p in sorted(codebase_path.glob(name))[:1]:
            if p.is_file():
                _add(p, "Setup")

    # 3) Top-level layout listing
    layout_lines: list[str] = []
    for p in sorted(codebase_path.iterdir()):
        if p.name in _DIR_BLOCKLIST or p.name.startswith("."):
            continue
        suffix = "/" if p.is_dir() else ""
        layout_lines.append(p.name + suffix)
    parts.append(
        "\n\n### Top-level layout\n```\n"
        + "\n".join(layout_lines[:60])
        + "\n```\n"
    )

    # 4) Strategic source files
    for group_name, globs in (
        ("Model", _MODEL_GLOBS),
        ("Train", _TRAIN_GLOBS),
        ("Data", _DATA_GLOBS),
        ("Forward / Eval", _FORWARD_GLOBS),
    ):
        seen = 0
        for pat in globs:
            for p in sorted(codebase_path.glob(pat)):
                if any(part in _DIR_BLOCKLIST for part in p.parts):
                    continue
                if not p.is_file():
                    continue
                if _add(p, group_name) and seen < 4:
                    seen += 1
                if seen >= 4 or total >= total_char_budget:
                    break
            if seen >= 4 or total >= total_char_budget:
                break

    bundle = "".join(parts)
    return bundle, files_added


_RESULT_RE = re.compile(r"<result>(.*?)</result>", re.DOTALL)


def _strip_result_tags(text: str) -> str:
    """If the LLM wrapped its response in ``<result>...</result>`` (per the
    ClaudeCodeClient prompt convention), pull out the inner content. Otherwise
    return the text as-is.
    """
    m = _RESULT_RE.search(text)
    return m.group(1).strip() if m else text.strip()


def run_codebase_analysis(
    *,
    codebase_path: Path,
    output_path: Path,
    skill_md_path: Path,
    wiki_root: Path,
    distilled_root: Path,
    llm: LLMClient,
    max_tokens: int = 8000,
) -> CodebaseAnalysis:
    """Run one codebase analysis. Returns a :class:`CodebaseAnalysis`; also
    writes the report to ``output_path``.

    The system prompt is the SKILL.md verbatim. The user prompt names the
    paths and includes the bundled file contents.
    """
    codebase_path = Path(codebase_path).resolve()
    output_path = Path(output_path)
    skill_md_path = Path(skill_md_path)
    wiki_root = Path(wiki_root)
    distilled_root = Path(distilled_root)

    if not skill_md_path.exists():
        raise FileNotFoundError(f"skill not found: {skill_md_path}")
    skill_text = skill_md_path.read_text()

    bundle_text, files_added = bundle_codebase(codebase_path)
    today = dt.date.today().isoformat()

    user = (
        f"Apply the codebase-analyzer skill to the codebase below.\n\n"
        f"- Codebase root: {codebase_path}\n"
        f"- Wiki root:     {wiki_root}\n"
        f"- Distillations: {distilled_root}\n"
        f"- Today:         {today}\n"
        f"- Output path:   {output_path}\n\n"
        f"## Bundled codebase context\n"
        f"The files below were pre-selected following the skill's heuristics. "
        f"If you have file-reading tools available, you may read additional "
        f"files from the codebase root for clarification — otherwise, base "
        f"your analysis on the bundle.\n"
        f"{bundle_text}\n\n"
        f"## Wiki context (from the personal-library)\n"
        f"Wiki root: `{wiki_root}`. Available files include `taxonomy.md`, "
        f"`architectures.md`, `index.md`, and per-category pages under "
        f"`categories/<cat>.md`. Per-paper distillations are at "
        f"`{distilled_root}/<category>/<paper_id>.md`.\n\n"
        f"## Output\n"
        f"Produce the full UPGRADE_PROPOSALS.md content as your response. "
        f"Wrap your final report in <result>...</result> tags so the runner "
        f"can extract it cleanly. Reasoning, file reads, etc. may appear "
        f"outside the tags.\n"
    )

    response = llm.complete(
        system=skill_text, user=user, max_tokens=max_tokens,
    )
    report = _strip_result_tags(response)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)

    return CodebaseAnalysis(
        output_path=output_path,
        report=report,
        bundle_size_chars=len(bundle_text),
        files_bundled=files_added,
    )
