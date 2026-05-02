import json

import pytest

from lib.query.route import route_query
from lib.llm.fake import FakeLLMClient


SAMPLE_INDEX = (
    "| paper_id | year | title | primary_category | one_line_summary | keywords |\n"
    "|----------|------|-------|------------------|------------------|----------|\n"
    "| 2024-a | 2024 | VLA Driver | vla | A VLA. | vla |\n"
    "| 2024-b | 2024 | Diffusion Decoder | diffusion_decoder | Diffusion. | diffusion |\n"
)


def test_route_returns_paper_ids():
    fake = FakeLLMClient(responses=[json.dumps({"paper_ids": ["2024-a"]})])
    out = route_query(question="Tell me about VLAs",
                      index_md=SAMPLE_INDEX, llm=fake, max_papers=5)
    assert out == ["2024-a"]


def test_route_filters_unknown_ids():
    fake = FakeLLMClient(responses=[
        json.dumps({"paper_ids": ["2024-a", "2024-bogus"]})
    ])
    out = route_query(question="x", index_md=SAMPLE_INDEX,
                      llm=fake, max_papers=5)
    assert out == ["2024-a"]


def test_route_respects_cap():
    fake = FakeLLMClient(responses=[
        json.dumps({"paper_ids": ["2024-a", "2024-b"]})
    ])
    out = route_query(question="x", index_md=SAMPLE_INDEX,
                      llm=fake, max_papers=1)
    assert out == ["2024-a"]


def test_route_empty_on_invalid_json():
    fake = FakeLLMClient(responses=["not json"])
    out = route_query(question="x", index_md=SAMPLE_INDEX,
                      llm=fake, max_papers=5)
    assert out == []
