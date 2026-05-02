"""Extract text from a PDF using PyMuPDF."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class ParseResult:
    text: str
    num_pages: int
    truncated: bool


_TRUNC_MARKER = "\n\n<!-- TRUNCATED -->\n"


def parse_pdf(path: Path, *, max_chars: int) -> ParseResult:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    parts: list[str] = []
    total = 0
    truncated = False
    with fitz.open(str(path)) as doc:
        for i, page in enumerate(doc, start=1):
            page_text = page.get_text("text") or ""
            sep = f"<!-- page {i} -->\n" if i > 1 else ""
            chunk = sep + page_text
            if total + len(chunk) > max_chars:
                remaining = max(0, max_chars - total)
                parts.append(chunk[:remaining])
                truncated = True
                break
            parts.append(chunk)
            total += len(chunk)
        num_pages = len(doc)
    text = "".join(parts).strip()
    if truncated:
        text += _TRUNC_MARKER
    return ParseResult(text=text, num_pages=num_pages, truncated=truncated)
