import json
from textwrap import dedent

import pytest

from lib.ingestion.summarize import summarize_paper, SummaryResult
from lib.llm.fake import FakeLLMClient


SAMPLE_FULL_MD = "Title: A Paper\nAbstract: We do diffusion."

VALID_JSON = json.dumps({
    "title": "A Paper",
    "authors": ["Alice", "Bob"],
    "year": 2024,
    "primary_category": "diffusion_decoder",
    "secondary_categories": ["world_model"],
    "keywords": ["diffusion", "policy"],
    "one_line_summary": "A diffusion policy for driving.",
    "notes_md": "## Method\nDiffusion.\n## Results\nGood.",
})


def test_summarize_returns_typed_result():
    fake = FakeLLMClient(responses=[VALID_JSON])
    out = summarize_paper(
        full_md=SAMPLE_FULL_MD,
        seed_taxonomy=["vla", "diffusion_decoder", "world_model", "misc"],
        llm=fake,
    )
    assert isinstance(out, SummaryResult)
    assert out.title == "A Paper"
    assert out.year == 2024
    assert out.primary_category == "diffusion_decoder"
    assert out.notes_md.startswith("## Method")


def test_summarize_includes_taxonomy_in_prompt():
    fake = FakeLLMClient(responses=[VALID_JSON])
    summarize_paper(
        full_md=SAMPLE_FULL_MD,
        seed_taxonomy=["vla", "world_model"],
        llm=fake,
    )
    user = fake.calls[0].user
    assert "vla" in user
    assert "world_model" in user
    assert SAMPLE_FULL_MD in user


def test_summarize_falls_back_to_misc_for_unknown_category():
    bad = json.dumps({
        "title": "x", "authors": [], "year": 2024,
        "primary_category": "BOGUS",
        "secondary_categories": [],
        "keywords": [], "one_line_summary": "s",
        "notes_md": "n",
    })
    fake = FakeLLMClient(responses=[bad])
    out = summarize_paper(
        full_md=SAMPLE_FULL_MD,
        seed_taxonomy=["vla", "misc"],
        llm=fake,
    )
    assert out.primary_category == "misc"


def test_summarize_strips_code_fences():
    fenced = "```json\n" + VALID_JSON + "\n```"
    fake = FakeLLMClient(responses=[fenced])
    out = summarize_paper(
        full_md=SAMPLE_FULL_MD,
        seed_taxonomy=["diffusion_decoder", "misc"],
        llm=fake,
    )
    assert out.title == "A Paper"


def test_summarize_invalid_json_raises():
    fake = FakeLLMClient(responses=["not json at all"])
    with pytest.raises(ValueError, match="LLM did not return valid JSON"):
        summarize_paper(
            full_md=SAMPLE_FULL_MD,
            seed_taxonomy=["misc"],
            llm=fake,
        )
