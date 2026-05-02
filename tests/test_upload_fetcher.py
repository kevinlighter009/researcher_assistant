from pathlib import Path

import pytest

from lib.ingestion.fetchers.upload import upload_fetch, FetchedSource


def test_upload_reads_bytes(tmp_path):
    pdf = tmp_path / "Cool Paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 ...")
    out = upload_fetch(pdf)
    assert isinstance(out, FetchedSource)
    assert out.raw_bytes == b"%PDF-1.4 ..."
    assert out.suggested_title == "Cool Paper"
    assert out.source_type == "upload"
    assert out.url is None
    assert out.arxiv_id is None


def test_upload_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        upload_fetch(tmp_path / "no.pdf")


def test_upload_rejects_non_pdf(tmp_path):
    other = tmp_path / "x.txt"
    other.write_text("hi")
    with pytest.raises(ValueError, match="must be a PDF"):
        upload_fetch(other)
