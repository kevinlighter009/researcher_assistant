from lib.query.answer import answer_from_notes
from lib.llm.fake import FakeLLMClient


def test_answer_includes_notes_in_prompt():
    fake = FakeLLMClient(responses=["A diffusion policy [2024-a]."])
    notes = {"2024-a": "Diffusion is X."}
    out = answer_from_notes(
        question="What is diffusion?", notes_by_id=notes, llm=fake,
    )
    assert out.answer.startswith("A diffusion")
    assert out.cited_paper_ids == ["2024-a"]
    user = fake.calls[0].user
    assert "Diffusion is X." in user
    assert "2024-a" in user


def test_answer_no_papers_returns_no_hit_notice():
    fake = FakeLLMClient(responses=["should not be called"])
    out = answer_from_notes(question="x", notes_by_id={}, llm=fake)
    assert "no library hit" in out.answer.lower()
    assert out.cited_paper_ids == []
    assert len(fake.calls) == 0


def test_answer_extracts_citations_from_text():
    fake = FakeLLMClient(responses=["Answer with [2024-a] and [2024-b]."])
    out = answer_from_notes(
        question="x",
        notes_by_id={"2024-a": "n1", "2024-b": "n2"},
        llm=fake,
    )
    assert sorted(out.cited_paper_ids) == ["2024-a", "2024-b"]


def test_answer_only_cites_ids_actually_supplied():
    fake = FakeLLMClient(responses=["Answer [2024-a] [2024-bogus]."])
    out = answer_from_notes(
        question="x",
        notes_by_id={"2024-a": "n1"},
        llm=fake,
    )
    assert out.cited_paper_ids == ["2024-a"]
