"""LLM-driven distillation: PDF -> SKILL.md-format Markdown file.

This module is the API-driven counterpart to the manual
``skills/paper-distillation/SKILL.md`` skill. Given a PDF, an
``LLMClient``, and an output path, it asks the LLM to produce a
Markdown file conforming to the SKILL.md schema (YAML front-matter +
fixed body section order), validates by re-parsing with
``parse_distilled_md``, and writes to disk. One corrective retry is
attempted on parse failure.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

from lib.indexing.from_distilled import parse_distilled_md
from lib.ingestion.pdf_parser import parse_pdf
from lib.llm.base import LLMClient


SEED_TAXONOMY = [
    "vla",
    "diffusion_decoder",
    "world_model",
    "e2e_planning",
    "perception",
    "datasets",
    "misc",
]


@dataclass
class DistillationResult:
    output_path: Path
    paper_id: str
    primary_category: str
    word_count: int
    truncated: bool  # True if PDF parse hit the char budget


# --- Prompt construction --------------------------------------------------

_SYSTEM_PROMPT = """You are a research-paper distillation assistant. You
read one paper and produce ONE Markdown file conforming exactly to the
schema below. The file will be parsed mechanically by a wiki generator,
so structure matters.

OUTPUT SCHEMA (in this order, no extras, no alternate orderings):

1. YAML front-matter delimited by `---` lines, with these fields:
   - paper_id            (string, format: "<year>-<slug>")
   - title               (string; quote if it contains a colon)
   - authors             (YAML list, e.g. [First Author, et al.])
   - year                (integer)
   - venue               (string, e.g. "CVPR 2025" or "arXiv")
   - arxiv_id            (string or null)
   - url                 (string or null)
   - primary_category    (one of the enum below)
   - secondary_categories (YAML list)
   - keywords            (YAML list, 5-8 short tokens)
   - one_line_summary    (string, <=200 chars)
   - distilled_at        (YYYY-MM-DD)
   - source_pdf          (string, relative path)

2. `# <Title>`  (H1, the paper title)
3. `## Keywords`               (FIRST body section, always)
4. `## TL;DR`
5. `## Problem & Motivation`
6. `## Innovation Points`
7. `## Model Architecture`
8. `## Benchmark Results`
9. `## Limitations & Open Questions`

`primary_category` MUST be exactly one of:
  vla, diffusion_decoder, world_model, e2e_planning, perception,
  datasets, misc

ANTI-PATTERNS (do not do):
- Renaming sections ("Method" instead of "Model Architecture").
- Putting `## Keywords` anywhere but first body section.
- Hyphenated enum values (e2e-planning instead of e2e_planning).
- Inventing benchmark numbers; write `not reported` when unknown.
- Omitting the YAML front-matter.

OUTPUT RULE: Return ONLY the Markdown file content, starting with
`---`. No code fences. No preamble. No trailing commentary.
"""


def _build_user_prompt(
    *,
    pdf_text: str,
    paper_id_hint: str,
    source_pdf: str,
    distilled_at: str,
) -> str:
    return (
        "Please distill the following research paper into the schema "
        "described in the system prompt.\n\n"
        f"Output context (use these verbatim in the front-matter):\n"
        f"- paper_id (hint, you may correct after reading): {paper_id_hint}\n"
        f"- source_pdf: {source_pdf}\n"
        f"- distilled_at: {distilled_at}\n\n"
        "Reminder: primary_category MUST be one of "
        f"{', '.join(SEED_TAXONOMY)}.\n\n"
        "=== BEGIN PAPER TEXT ===\n"
        f"{pdf_text}\n"
        "=== END PAPER TEXT ===\n"
    )


# --- Code-fence stripping -------------------------------------------------

_FENCE_OPEN_RE = re.compile(r"^```[a-zA-Z0-9_-]*\s*\n")
_FENCE_CLOSE_RE = re.compile(r"\n```\s*$")


def _strip_code_fences(text: str) -> str:
    """If ``text`` is wrapped in a single ```` ``` ```` block, strip the
    fences. Otherwise return as-is (only leading/trailing whitespace
    trimmed).
    """
    s = text.strip()
    if s.startswith("```"):
        s = _FENCE_OPEN_RE.sub("", s, count=1)
        s = _FENCE_CLOSE_RE.sub("", s, count=1)
        s = s.strip()
    return s


# --- Public API -----------------------------------------------------------

def distill_pdf_via_api(
    *,
    pdf_path: Path,
    output_path: Path,
    llm: LLMClient,
    max_full_md_chars: int = 240_000,
    max_tokens: int = 4096,
) -> DistillationResult:
    """Read a PDF, ask the LLM for a SKILL.md-format distillation,
    validate, and write the file. Raises ``ValueError`` if the LLM
    output cannot be parsed even after one retry with a corrective
    prompt.
    """
    pdf_path = Path(pdf_path)
    output_path = Path(output_path)

    parsed_pdf = parse_pdf(pdf_path, max_chars=max_full_md_chars)

    paper_id_hint = output_path.stem
    distilled_at = dt.date.today().isoformat()
    source_pdf = str(pdf_path)

    user_prompt = _build_user_prompt(
        pdf_text=parsed_pdf.text,
        paper_id_hint=paper_id_hint,
        source_pdf=source_pdf,
        distilled_at=distilled_at,
    )

    # First attempt
    raw = llm.complete(
        system=_SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=max_tokens,
    )
    md_text = _strip_code_fences(raw)

    last_error: Exception | None = None
    paper = _try_write_and_parse(md_text, output_path)
    if paper is None:
        # Retry once with a corrective prompt
        last_error = _last_parse_error(md_text)
        retry_user = (
            f"Your previous output failed to parse: {last_error}. "
            "Return a corrected complete Markdown file. "
            "Remember: start with `---`, no code fences, no preamble. "
            "Original request follows.\n\n"
            + user_prompt
        )
        raw2 = llm.complete(
            system=_SYSTEM_PROMPT,
            user=retry_user,
            max_tokens=max_tokens,
        )
        md_text = _strip_code_fences(raw2)
        paper = _try_write_and_parse(md_text, output_path)
        if paper is None:
            # Make sure we don't leave a half-written file behind.
            if output_path.exists():
                output_path.unlink()
            err = _last_parse_error(md_text)
            raise ValueError(
                f"LLM distillation could not be parsed after retry: {err}"
            )

    return DistillationResult(
        output_path=output_path,
        paper_id=str(paper.front_matter.get("paper_id", "")),
        primary_category=str(
            paper.front_matter.get("primary_category", "misc") or "misc"
        ),
        word_count=len(md_text.split()),
        truncated=parsed_pdf.truncated,
    )


def _try_write_and_parse(md_text: str, output_path: Path):
    """Write ``md_text`` to ``output_path`` and re-parse it. Returns the
    parsed paper on success, ``None`` on parse failure (the file is
    removed in the failure case so the caller can decide what to do).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md_text)
    try:
        return parse_distilled_md(output_path)
    except Exception:
        if output_path.exists():
            output_path.unlink()
        return None


def _last_parse_error(md_text: str) -> str:
    """Re-derive a one-line description of why ``md_text`` is unparseable
    (used in the corrective retry prompt and the final exception).
    """
    if not md_text.lstrip().startswith("---"):
        return "output does not start with YAML front-matter delimiter '---'"
    return "front-matter or section structure invalid"
