from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
import pytest

from lib.distillation.api_distill import (
    DistillationResult,
    SEED_TAXONOMY,
    distill_pdf_via_api,
)
from lib.indexing.from_distilled import parse_distilled_md
from lib.llm.fake import FakeLLMClient


VALID_DISTILLATION = '''---
paper_id: 2024-mockpaper
title: "MockPaper: A Mocked Paper"
authors: [Mock Author]
year: 2024
venue: arXiv
arxiv_id: null
url: null
primary_category: misc
secondary_categories: []
keywords: [mock, test]
one_line_summary: A mocked paper for testing.
distilled_at: 2026-05-02
source_pdf: tests/fixtures/mockpaper.pdf
---

# MockPaper: A Mocked Paper

## Keywords
- mock, test

## TL;DR
Mock TL;DR.

## Problem & Motivation
Mock motivation.

## Innovation Points
- **Mocked** — for testing.

## Model Architecture
- Mock arch.

## Benchmark Results
Mock results.

## Limitations & Open Questions
Mock limits.
'''


def make_tiny_pdf(path: Path, pages_text: list[str]) -> None:
    doc = fitz.open()
    for txt in pages_text:
        page = doc.new_page()
        page.insert_text((72, 72), txt)
    doc.save(str(path))
    doc.close()


def _make_pdf(tmp_path: Path, text: str = "Some paper content") -> Path:
    pdf = tmp_path / "mockpaper.pdf"
    make_tiny_pdf(pdf, [text])
    return pdf


def test_distill_writes_valid_md(tmp_path, mocker):
    pdf = _make_pdf(tmp_path)
    out = tmp_path / "out" / "2024-mockpaper.md"
    llm = FakeLLMClient(responses=[VALID_DISTILLATION])

    result = distill_pdf_via_api(
        pdf_path=pdf,
        output_path=out,
        llm=llm,
    )

    assert isinstance(result, DistillationResult)
    assert out.exists()
    parsed = parse_distilled_md(out)
    assert parsed.front_matter["paper_id"] == "2024-mockpaper"
    assert result.paper_id == "2024-mockpaper"
    assert result.primary_category == "misc"
    assert result.word_count > 0


def test_distill_strips_code_fences(tmp_path, mocker):
    pdf = _make_pdf(tmp_path)
    out = tmp_path / "out" / "2024-mockpaper.md"
    fenced = "```markdown\n" + VALID_DISTILLATION + "\n```"
    llm = FakeLLMClient(responses=[fenced])

    result = distill_pdf_via_api(
        pdf_path=pdf,
        output_path=out,
        llm=llm,
    )

    text = out.read_text()
    # Must start with YAML front-matter, not a fence
    assert text.startswith("---")
    assert "```" not in text.splitlines()[0]
    parsed = parse_distilled_md(out)
    assert parsed.front_matter["paper_id"] == "2024-mockpaper"
    assert result.paper_id == "2024-mockpaper"


def test_distill_retries_on_invalid_output(tmp_path, mocker):
    pdf = _make_pdf(tmp_path)
    out = tmp_path / "out" / "2024-mockpaper.md"
    llm = FakeLLMClient(responses=["not valid", VALID_DISTILLATION])

    result = distill_pdf_via_api(
        pdf_path=pdf,
        output_path=out,
        llm=llm,
    )

    assert len(llm.calls) == 2
    assert out.exists()
    parsed = parse_distilled_md(out)
    assert parsed.front_matter["paper_id"] == "2024-mockpaper"
    assert isinstance(result, DistillationResult)


def test_distill_raises_after_two_failures(tmp_path, mocker):
    pdf = _make_pdf(tmp_path)
    out = tmp_path / "out" / "2024-mockpaper.md"
    llm = FakeLLMClient(responses=["not valid", "still not valid"])

    with pytest.raises(ValueError):
        distill_pdf_via_api(
            pdf_path=pdf,
            output_path=out,
            llm=llm,
        )

    assert not out.exists()


def test_distill_includes_pdf_text_in_user_prompt(tmp_path, mocker):
    pdf = _make_pdf(tmp_path, text="DISTINCTIVE-SENTINEL-XYZ inside paper body")
    out = tmp_path / "out" / "2024-mockpaper.md"
    llm = FakeLLMClient(responses=[VALID_DISTILLATION])

    distill_pdf_via_api(
        pdf_path=pdf,
        output_path=out,
        llm=llm,
    )

    assert len(llm.calls) >= 1
    assert "DISTINCTIVE-SENTINEL-XYZ" in llm.calls[0].user


def test_distill_passes_taxonomy_in_system_or_user(tmp_path, mocker):
    pdf = _make_pdf(tmp_path)
    out = tmp_path / "out" / "2024-mockpaper.md"
    llm = FakeLLMClient(responses=[VALID_DISTILLATION])

    distill_pdf_via_api(
        pdf_path=pdf,
        output_path=out,
        llm=llm,
    )

    combined = llm.calls[0].system + "\n" + llm.calls[0].user
    for value in SEED_TAXONOMY:
        assert value in combined, f"taxonomy value {value!r} missing from prompt"
