import json
import sys
from pathlib import Path

import fitz
import pytest

import cli


SUMMARY = json.dumps({
    "title": "Test Paper", "authors": ["A"], "year": 2024,
    "primary_category": "vla", "secondary_categories": [],
    "keywords": ["k"], "one_line_summary": "s",
    "notes_md": "n",
})


@pytest.fixture
def fake_project(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "default.yaml").write_text(
        f"data_dir: {tmp_path / 'data'}\n"
        "llm:\n  default_backend: fake\n"
        "  anthropic: {model: m, max_tokens: 1, temperature: 0.0}\n"
        "seed_taxonomy: [vla, misc]\n"
        "ingest: {max_full_md_chars: 10000}\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return tmp_path


def make_pdf(tmp_path: Path) -> Path:
    p = tmp_path / "paper.pdf"
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "hello")
    doc.save(str(p))
    doc.close()
    return p


def test_cli_ingest(fake_project, monkeypatch, capsys):
    pdf = make_pdf(fake_project)
    from lib.llm.fake import FakeLLMClient
    monkeypatch.setattr(cli, "_make_llm_client",
                        lambda cfg, backend: FakeLLMClient(responses=[SUMMARY]))
    rc = cli.main(["ingest", str(pdf)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ingested" in out
    assert (fake_project / "data" / "wiki" / "index.md").exists()


def test_cli_query(fake_project, monkeypatch, capsys):
    pdf = make_pdf(fake_project)
    from lib.llm.fake import FakeLLMClient
    monkeypatch.setattr(cli, "_make_llm_client",
                        lambda cfg, backend: FakeLLMClient(responses=[SUMMARY]))
    cli.main(["ingest", str(pdf)])
    monkeypatch.setattr(
        cli, "_make_llm_client",
        lambda cfg, backend: FakeLLMClient(responses=[
            json.dumps({"paper_ids": ["2024-test-paper"]}),
            "answered [2024-test-paper]",
        ]),
    )
    rc = cli.main(["query", "what is this"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "answered" in out


def test_cli_rebuild_index(fake_project, monkeypatch, capsys):
    pdf = make_pdf(fake_project)
    from lib.llm.fake import FakeLLMClient
    monkeypatch.setattr(cli, "_make_llm_client",
                        lambda cfg, backend: FakeLLMClient(responses=[SUMMARY]))
    cli.main(["ingest", str(pdf)])
    # corrupt the index
    idx = fake_project / "data" / "wiki" / "index.md"
    idx.write_text("CORRUPT")
    rc = cli.main(["rebuild-index"])
    assert rc == 0
    assert "2024-test-paper" in idx.read_text()
