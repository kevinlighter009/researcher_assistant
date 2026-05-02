import json

from lib.query.orchestrator import query_wiki, QueryResult
from lib.indexing.writer import WikiPaths, upsert_paper_in_wiki
from lib.llm.fake import FakeLLMClient
from lib.storage import PaperStorage
from lib.models import PaperMeta


def setup_corpus(tmp_path):
    storage = PaperStorage(tmp_path)
    paths = WikiPaths(tmp_path / "wiki")
    for pid, cat in [("2024-a", "vla"), ("2024-b", "world_model")]:
        storage.paper_dir(pid).mkdir(parents=True)
        storage.write_meta(PaperMeta(
            paper_id=pid, title=f"T-{pid}", authors=[], year=2024,
            primary_category=cat, ingested_at="t", source_type="upload",
            content_hash=pid,
            one_line_summary=f"sum-{pid}", notes_status="ok",
        ))
        (storage.paper_dir(pid) / "notes.md").write_text(f"NOTES-{pid}")
        upsert_paper_in_wiki(storage.read_meta(pid), paths)
    return storage, paths


def test_query_end_to_end(tmp_path):
    storage, paths = setup_corpus(tmp_path)
    fake = FakeLLMClient(responses=[
        json.dumps({"paper_ids": ["2024-a"]}),     # pass 1
        "answer using [2024-a]",                    # pass 2
    ])
    result = query_wiki(question="hi", storage=storage, wiki_paths=paths,
                        llm=fake, max_papers=5)
    assert isinstance(result, QueryResult)
    assert result.answer == "answer using [2024-a]"
    assert result.routed_paper_ids == ["2024-a"]
    assert result.cited_paper_ids == ["2024-a"]
    # pass 2 saw the actual notes.md content
    pass2_user = fake.calls[1].user
    assert "NOTES-2024-a" in pass2_user


def test_query_no_route_short_circuits(tmp_path):
    storage, paths = setup_corpus(tmp_path)
    fake = FakeLLMClient(responses=[json.dumps({"paper_ids": []})])
    result = query_wiki(question="hi", storage=storage, wiki_paths=paths,
                        llm=fake, max_papers=5)
    assert "no library hit" in result.answer.lower()
    assert len(fake.calls) == 1  # only pass 1 was made
