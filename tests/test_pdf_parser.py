from pathlib import Path

import fitz  # PyMuPDF
import pytest

from lib.ingestion.pdf_parser import parse_pdf, ParseResult


def make_tiny_pdf(path: Path, pages_text: list[str]) -> None:
    doc = fitz.open()
    for txt in pages_text:
        page = doc.new_page()
        page.insert_text((72, 72), txt)
    doc.save(str(path))
    doc.close()


def test_parse_pdf_basic(tmp_path):
    pdf = tmp_path / "x.pdf"
    make_tiny_pdf(pdf, ["Hello world", "Second page"])
    result = parse_pdf(pdf, max_chars=10000)
    assert isinstance(result, ParseResult)
    assert "Hello world" in result.text
    assert "Second page" in result.text
    assert "<!-- page 2 -->" in result.text
    assert result.truncated is False
    assert result.num_pages == 2


def test_parse_pdf_truncation(tmp_path):
    pdf = tmp_path / "x.pdf"
    make_tiny_pdf(pdf, ["Hello " * 200])
    result = parse_pdf(pdf, max_chars=50)
    assert len(result.text) <= 50 + 200  # allow a bit of slack for marker
    assert result.truncated is True


def test_parse_pdf_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_pdf(tmp_path / "no.pdf", max_chars=100)
