# Personal Library — Core (Plan 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the LLM-wiki core — a CLI tool that ingests local PDFs of autonomous-driving papers, has the LLM produce per-paper deep notes, maintains human-readable wiki index files, and answers queries via two-pass routing (LLM picks papers from index → LLM answers from those papers' notes).

**Architecture:** Five well-bounded Python modules (`ingestion/`, `indexing/`, `query/`, `llm/`, plus shared `models/` and `config/`) communicating only through (a) a typed `LLMClient` protocol and (b) a strict on-disk file layout where `papers/<id>/meta.json` is the source of truth and `wiki/*.md` is rebuildable from it. No database, no embeddings, no network for the core test suite.

**Tech Stack:** Python 3.11, conda, `anthropic` SDK, PyMuPDF (`fitz`), `pydantic` for models, `pyyaml` for config, `pytest` for tests, `python-dotenv` for secrets, plain stdlib `argparse` for CLI. Streamlit and remote fetchers are deferred to Plan 2.

**Reference spec:** `docs/superpowers/specs/2026-05-02-personal-library-llm-wiki-design.md`

---

## File Structure

This plan creates the following layout. Each file has one clear responsibility; nothing imports across module boundaries except through the public `__init__.py` of each module.

```
personal_library/
├── environment.yml                  # conda env definition
├── pyproject.toml                   # package metadata + pytest config
├── .gitignore
├── .env.example                     # template for ANTHROPIC_API_KEY
├── README.md                        # quickstart
├── config/
│   └── default.yaml                 # default config (paths, LLM, taxonomy)
├── lib/
│   ├── __init__.py
│   ├── config.py                    # load + merge default.yaml/local.yaml/env
│   ├── models.py                    # pydantic: PaperMeta, IngestResult
│   ├── storage.py                   # paper_id alloc, paths, hash, read/write
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py                  # LLMClient Protocol
│   │   ├── fake.py                  # FakeLLMClient for tests
│   │   ├── anthropic_client.py      # AnthropicClient
│   │   └── claude_code_client.py    # ClaudeCodeClient (subprocess)
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── pdf_parser.py            # PyMuPDF → full.md
│   │   ├── fetchers/
│   │   │   ├── __init__.py
│   │   │   └── upload.py            # local PDF upload fetcher
│   │   ├── summarize.py             # LLM call: full.md → notes.md + meta
│   │   └── orchestrator.py          # ties fetcher → parser → summarize → write
│   ├── indexing/
│   │   ├── __init__.py
│   │   ├── writer.py                # append/update index.md + category file
│   │   └── rebuild.py               # regenerate wiki/ from papers/*/meta.json
│   └── query/
│       ├── __init__.py
│       ├── route.py                 # pass 1: pick paper_ids
│       ├── answer.py                # pass 2: read notes, answer
│       └── orchestrator.py          # ties pass 1 + pass 2
├── cli.py                           # argparse CLI: ingest, query, rebuild-index
└── tests/
    ├── __init__.py
    ├── conftest.py                  # shared fixtures
    ├── fixtures/
    │   ├── tiny.pdf                 # 1-page sample PDF, generated in test
    │   └── sample_paper.md          # minimal full.md example
    ├── test_config.py
    ├── test_models.py
    ├── test_storage.py
    ├── test_llm_fake.py
    ├── test_pdf_parser.py
    ├── test_summarize.py
    ├── test_upload_fetcher.py
    ├── test_ingestion_orchestrator.py
    ├── test_indexing_writer.py
    ├── test_indexing_rebuild.py
    ├── test_query_route.py
    ├── test_query_answer.py
    ├── test_query_orchestrator.py
    └── test_cli.py
```

**Boundary rules enforced by tests:**
- `ingestion/` never imports from `indexing/` or `query/`.
- `indexing/` never imports from `ingestion/` or `query/`.
- `query/` never imports from `ingestion/` or `indexing/`.
- Anything that talks to an LLM goes through `lib/llm`.
- The CLI orchestrates by calling module-level functions; no domain logic in `cli.py`.

---

## Task 1: Project skeleton & conda env

**Files:**
- Create: `environment.yml`
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`
- Create: `lib/__init__.py` (empty)
- Create: `tests/__init__.py` (empty)

- [ ] **Step 1: Write `environment.yml`**

```yaml
name: personal_library
channels:
  - conda-forge
dependencies:
  - python=3.11
  - pip
  - pip:
      - anthropic>=0.34.0
      - pymupdf>=1.24.0
      - pydantic>=2.6
      - pyyaml>=6.0
      - python-dotenv>=1.0
      - pytest>=8.0
      - pytest-mock>=3.12
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "personal_library"
version = "0.1.0"
requires-python = ">=3.11"

[tool.setuptools.packages.find]
include = ["lib*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

- [ ] **Step 3: Write `.gitignore`**

```
# python
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
build/
dist/

# user data and secrets
data/
.env
config/local.yaml
```

- [ ] **Step 4: Write `.env.example`**

```
# Copy to .env and fill in. .env is gitignored.
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

- [ ] **Step 5: Write `README.md`**

```markdown
# Personal Library

A local LLM-maintained wiki for research papers, inspired by Karpathy's "LLM wiki" idea.

## Setup
\`\`\`
conda env create -f environment.yml
conda activate personal_library
cp .env.example .env  # then edit
\`\`\`

## Usage (CLI)
\`\`\`
python cli.py ingest path/to/paper.pdf
python cli.py query "What is the latest on diffusion policies for driving?"
python cli.py rebuild-index
\`\`\`

See `docs/superpowers/specs/` for design.
```

- [ ] **Step 6: Create empty `lib/__init__.py` and `tests/__init__.py`**

```bash
touch lib/__init__.py tests/__init__.py
```

- [ ] **Step 7: Create the conda env and verify**

```bash
conda env create -f environment.yml
conda activate personal_library
python -c "import anthropic, fitz, pydantic, yaml; print('ok')"
```
Expected: prints `ok`.

- [ ] **Step 8: Commit**

```bash
git add environment.yml pyproject.toml .gitignore .env.example README.md lib/__init__.py tests/__init__.py
git commit -m "chore: project skeleton, conda env, gitignore"
```

---

## Task 2: Configuration loader

**Files:**
- Create: `config/default.yaml`
- Create: `lib/config.py`
- Test: `tests/test_config.py`

**What it does:** Loads `config/default.yaml`, deep-merges optional `config/local.yaml`, and exposes a typed `Config` object. API keys come from `.env` via `python-dotenv` and are surfaced through `Config.anthropic_api_key`.

- [ ] **Step 1: Write `config/default.yaml`**

```yaml
data_dir: ./data
llm:
  default_backend: anthropic   # or claude_code
  anthropic:
    model: claude-sonnet-4-5-20250929
    max_tokens: 4096
    temperature: 0.2
  claude_code:
    binary: claude
seed_taxonomy:
  - vla
  - diffusion_decoder
  - world_model
  - e2e_planning
  - perception
  - datasets
  - misc
ingest:
  max_full_md_chars: 240000   # ~60k tokens, summarization input cap
```

- [ ] **Step 2: Write the failing test in `tests/test_config.py`**

```python
import os
import textwrap
from pathlib import Path

import pytest

from lib.config import load_config


def test_load_default(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "default.yaml").write_text(textwrap.dedent("""
        data_dir: ./data
        llm:
          default_backend: anthropic
          anthropic:
            model: m1
            max_tokens: 100
            temperature: 0.1
        seed_taxonomy: [a, b]
        ingest:
          max_full_md_chars: 1000
    """).strip())
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = load_config()
    assert cfg.data_dir == Path("./data")
    assert cfg.llm.default_backend == "anthropic"
    assert cfg.llm.anthropic.model == "m1"
    assert cfg.seed_taxonomy == ["a", "b"]
    assert cfg.ingest.max_full_md_chars == 1000
    assert cfg.anthropic_api_key is None


def test_local_override(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "default.yaml").write_text(
        "data_dir: ./data\n"
        "llm:\n  default_backend: anthropic\n"
        "  anthropic: {model: m1, max_tokens: 100, temperature: 0.1}\n"
        "seed_taxonomy: [a]\n"
        "ingest: {max_full_md_chars: 1}\n"
    )
    (cfg_dir / "local.yaml").write_text("llm:\n  anthropic:\n    model: m2\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = load_config()
    assert cfg.llm.anthropic.model == "m2"
    assert cfg.llm.anthropic.max_tokens == 100  # preserved


def test_env_api_key(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    (cfg_dir / "default.yaml").write_text(
        "data_dir: ./data\n"
        "llm:\n  default_backend: anthropic\n"
        "  anthropic: {model: m1, max_tokens: 1, temperature: 0.0}\n"
        "seed_taxonomy: [a]\n"
        "ingest: {max_full_md_chars: 1}\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    cfg = load_config()
    assert cfg.anthropic_api_key == "sk-ant-test"
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lib.config'`.

- [ ] **Step 4: Implement `lib/config.py`**

```python
"""Load and merge YAML config files; surface API keys from env."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel


class AnthropicCfg(BaseModel):
    model: str
    max_tokens: int
    temperature: float


class ClaudeCodeCfg(BaseModel):
    binary: str = "claude"


class LLMCfg(BaseModel):
    default_backend: str
    anthropic: AnthropicCfg
    claude_code: ClaudeCodeCfg = ClaudeCodeCfg()


class IngestCfg(BaseModel):
    max_full_md_chars: int


class Config(BaseModel):
    data_dir: Path
    llm: LLMCfg
    seed_taxonomy: list[str]
    ingest: IngestCfg
    anthropic_api_key: Optional[str] = None


def _deep_merge(base: dict, overlay: dict) -> dict:
    out = dict(base)
    for k, v in overlay.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(config_dir: Path | None = None) -> Config:
    config_dir = config_dir or Path.cwd() / "config"
    default_path = config_dir / "default.yaml"
    if not default_path.exists():
        raise FileNotFoundError(f"missing {default_path}")
    data = yaml.safe_load(default_path.read_text()) or {}
    local_path = config_dir / "local.yaml"
    if local_path.exists():
        local = yaml.safe_load(local_path.read_text()) or {}
        data = _deep_merge(data, local)
    load_dotenv(Path.cwd() / ".env", override=False)
    data["anthropic_api_key"] = os.environ.get("ANTHROPIC_API_KEY")
    return Config.model_validate(data)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add config/default.yaml lib/config.py tests/test_config.py
git commit -m "feat(config): typed config loader with default+local merge"
```

---

## Task 3: Domain models (PaperMeta, IngestResult)

**Files:**
- Create: `lib/models.py`
- Test: `tests/test_models.py`

**What it does:** Defines the typed schema for `meta.json` (the source of truth) and the return type of an ingestion call. Using pydantic so we get free JSON serialization plus validation.

- [ ] **Step 1: Write the failing test in `tests/test_models.py`**

```python
import json
import pytest
from pydantic import ValidationError

from lib.models import PaperMeta, IngestResult


def test_paper_meta_round_trip():
    m = PaperMeta(
        paper_id="2024-2406.12345",
        title="A Driving World Model",
        authors=["Alice", "Bob"],
        year=2024,
        arxiv_id="2406.12345",
        url=None,
        keywords=["world model", "diffusion"],
        primary_category="world_model",
        secondary_categories=["diffusion_decoder"],
        ingested_at="2026-05-02T10:00:00Z",
        source_type="upload",
        content_hash="deadbeef",
        one_line_summary="A diffusion world model for driving.",
        notes_status="ok",
    )
    j = m.model_dump_json()
    m2 = PaperMeta.model_validate_json(j)
    assert m2 == m


def test_paper_meta_requires_paper_id():
    with pytest.raises(ValidationError):
        PaperMeta(title="x", authors=[], year=2024,
                  primary_category="misc",
                  ingested_at="t", source_type="upload",
                  content_hash="h", one_line_summary="s",
                  notes_status="ok")


def test_paper_meta_notes_status_enum():
    with pytest.raises(ValidationError):
        PaperMeta(
            paper_id="x", title="x", authors=[], year=2024,
            primary_category="misc", ingested_at="t",
            source_type="upload", content_hash="h",
            one_line_summary="s", notes_status="bogus",
        )


def test_ingest_result_shape():
    r = IngestResult(paper_id="x", created=True, message="ok")
    assert r.created is True
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lib.models'`.

- [ ] **Step 3: Implement `lib/models.py`**

```python
"""Typed domain models. PaperMeta corresponds to papers/<id>/meta.json."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


NotesStatus = Literal["ok", "pending", "failed"]
SourceType = Literal["upload", "arxiv", "web", "search"]


class PaperMeta(BaseModel):
    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int
    arxiv_id: Optional[str] = None
    url: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    primary_category: str
    secondary_categories: list[str] = Field(default_factory=list)
    ingested_at: str  # ISO 8601 UTC
    source_type: SourceType
    content_hash: str
    one_line_summary: str
    notes_status: NotesStatus = "pending"
    full_md_truncated: bool = False


class IngestResult(BaseModel):
    paper_id: str
    created: bool   # False if already existed
    message: str
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add lib/models.py tests/test_models.py
git commit -m "feat(models): PaperMeta + IngestResult pydantic schemas"
```

---

## Task 4: Storage helpers (paths, paper_id, hash)

**Files:**
- Create: `lib/storage.py`
- Test: `tests/test_storage.py`

**What it does:** Generates `paper_id`s of the form `<year>-<slug>`, computes content hashes for dedup, returns `Path` objects for a paper's directory and its files, reads/writes `meta.json` atomically, and lists existing papers.

- [ ] **Step 1: Write the failing test in `tests/test_storage.py`**

```python
import json
from pathlib import Path

import pytest

from lib.storage import (
    PaperStorage, content_hash, allocate_paper_id, slugify,
)
from lib.models import PaperMeta


def make_meta(paper_id: str, year: int = 2024, hash_: str = "abc") -> PaperMeta:
    return PaperMeta(
        paper_id=paper_id, title="t", authors=[], year=year,
        primary_category="misc", ingested_at="2026-05-02T00:00:00Z",
        source_type="upload", content_hash=hash_,
        one_line_summary="s", notes_status="pending",
    )


def test_content_hash_stable():
    assert content_hash(b"abc") == content_hash(b"abc")
    assert content_hash(b"abc") != content_hash(b"abd")


def test_slugify():
    assert slugify("Hello, World! 2024") == "hello-world-2024"
    assert slugify("  a   b  ") == "a-b"
    assert slugify("π—λ") == "unknown"  # non-ascii fallback


def test_allocate_paper_id_unique(tmp_path):
    storage = PaperStorage(tmp_path)
    a = allocate_paper_id(storage, year=2024, slug_hint="vla-paper")
    storage.paper_dir(a).mkdir(parents=True)
    storage.write_meta(make_meta(a))
    b = allocate_paper_id(storage, year=2024, slug_hint="vla-paper")
    assert a == "2024-vla-paper"
    assert b == "2024-vla-paper-2"


def test_paper_dir_paths(tmp_path):
    storage = PaperStorage(tmp_path)
    pdir = storage.paper_dir("2024-x")
    assert pdir == tmp_path / "papers" / "2024-x"
    assert storage.source_pdf_path("2024-x") == pdir / "source.pdf"
    assert storage.full_md_path("2024-x") == pdir / "full.md"
    assert storage.notes_md_path("2024-x") == pdir / "notes.md"
    assert storage.meta_json_path("2024-x") == pdir / "meta.json"


def test_write_then_read_meta(tmp_path):
    storage = PaperStorage(tmp_path)
    storage.paper_dir("2024-x").mkdir(parents=True)
    storage.write_meta(make_meta("2024-x"))
    m = storage.read_meta("2024-x")
    assert m.paper_id == "2024-x"


def test_list_paper_ids(tmp_path):
    storage = PaperStorage(tmp_path)
    for pid in ("2024-a", "2024-b"):
        storage.paper_dir(pid).mkdir(parents=True)
        storage.write_meta(make_meta(pid))
    assert sorted(storage.list_paper_ids()) == ["2024-a", "2024-b"]


def test_find_by_hash(tmp_path):
    storage = PaperStorage(tmp_path)
    storage.paper_dir("2024-a").mkdir(parents=True)
    storage.write_meta(make_meta("2024-a", hash_="h1"))
    assert storage.find_by_hash("h1") == "2024-a"
    assert storage.find_by_hash("nope") is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lib.storage'`.

- [ ] **Step 3: Implement `lib/storage.py`**

```python
"""Filesystem layer for papers/. meta.json is the source of truth."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Iterable, Optional

from lib.models import PaperMeta


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def slugify(text: str) -> str:
    if not text:
        return "unknown"
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = nfkd.encode("ascii", "ignore").decode("ascii")
    ascii_text = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return ascii_text or "unknown"


class PaperStorage:
    """Directory layout: <root>/papers/<paper_id>/{source.pdf,full.md,notes.md,meta.json}."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)

    @property
    def papers_root(self) -> Path:
        return self.data_dir / "papers"

    def paper_dir(self, paper_id: str) -> Path:
        return self.papers_root / paper_id

    def source_pdf_path(self, paper_id: str) -> Path:
        return self.paper_dir(paper_id) / "source.pdf"

    def full_md_path(self, paper_id: str) -> Path:
        return self.paper_dir(paper_id) / "full.md"

    def notes_md_path(self, paper_id: str) -> Path:
        return self.paper_dir(paper_id) / "notes.md"

    def meta_json_path(self, paper_id: str) -> Path:
        return self.paper_dir(paper_id) / "meta.json"

    def write_meta(self, meta: PaperMeta) -> None:
        path = self.meta_json_path(meta.paper_id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(meta.model_dump_json(indent=2))
        tmp.replace(path)

    def read_meta(self, paper_id: str) -> PaperMeta:
        return PaperMeta.model_validate_json(self.meta_json_path(paper_id).read_text())

    def list_paper_ids(self) -> list[str]:
        if not self.papers_root.exists():
            return []
        return [p.name for p in self.papers_root.iterdir()
                if p.is_dir() and (p / "meta.json").exists()]

    def iter_metas(self) -> Iterable[PaperMeta]:
        for pid in self.list_paper_ids():
            yield self.read_meta(pid)

    def find_by_hash(self, h: str) -> Optional[str]:
        for m in self.iter_metas():
            if m.content_hash == h:
                return m.paper_id
        return None


def allocate_paper_id(storage: PaperStorage, year: int, slug_hint: str) -> str:
    base = f"{year}-{slugify(slug_hint)}"
    if not storage.paper_dir(base).exists():
        return base
    for i in range(2, 100):
        cand = f"{base}-{i}"
        if not storage.paper_dir(cand).exists():
            return cand
    raise RuntimeError(f"too many collisions on paper_id base {base}")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_storage.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add lib/storage.py tests/test_storage.py
git commit -m "feat(storage): paper_id alloc, paths, hash, meta.json IO"
```

---

## Task 5: LLMClient protocol + FakeLLMClient

**Files:**
- Create: `lib/llm/__init__.py`
- Create: `lib/llm/base.py`
- Create: `lib/llm/fake.py`
- Test: `tests/test_llm_fake.py`

**What it does:** Defines the single interface every higher module uses to talk to an LLM, plus a fake that returns scripted responses for tests. After this task, the rest of the plan can be implemented and tested without ever calling a real LLM.

- [ ] **Step 1: Write the failing test in `tests/test_llm_fake.py`**

```python
import pytest

from lib.llm.fake import FakeLLMClient


def test_fake_returns_scripted():
    c = FakeLLMClient(responses=["hello", "world"])
    assert c.complete(system="s", user="u1") == "hello"
    assert c.complete(system="s", user="u2") == "world"


def test_fake_records_calls():
    c = FakeLLMClient(responses=["x"])
    c.complete(system="sys", user="usr", max_tokens=10, temperature=0.5)
    assert len(c.calls) == 1
    call = c.calls[0]
    assert call.system == "sys"
    assert call.user == "usr"
    assert call.max_tokens == 10
    assert call.temperature == 0.5


def test_fake_callable_response():
    def resp(system, user, **kw):
        return f"echo:{user}"
    c = FakeLLMClient(responses=resp)
    assert c.complete(system="s", user="hi") == "echo:hi"
    assert c.complete(system="s", user="bye") == "echo:bye"


def test_fake_runs_out():
    c = FakeLLMClient(responses=["only one"])
    c.complete(system="s", user="u")
    with pytest.raises(IndexError):
        c.complete(system="s", user="u")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_llm_fake.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lib.llm.fake'`.

- [ ] **Step 3: Implement `lib/llm/__init__.py`**

```python
from lib.llm.base import LLMClient
from lib.llm.fake import FakeLLMClient

__all__ = ["LLMClient", "FakeLLMClient"]
```

- [ ] **Step 4: Implement `lib/llm/base.py`**

```python
"""The single LLM interface used by every higher-level module."""
from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> str: ...
```

- [ ] **Step 5: Implement `lib/llm/fake.py`**

```python
"""Test double for LLMClient. Scripted responses or a callable."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Union


@dataclass
class _RecordedCall:
    system: str
    user: str
    max_tokens: int
    temperature: float


class FakeLLMClient:
    def __init__(
        self,
        responses: Union[Iterable[str], Callable[..., str]],
    ):
        if callable(responses):
            self._fn = responses
            self._queue = None
        else:
            self._fn = None
            self._queue = list(responses)
        self.calls: list[_RecordedCall] = []

    def complete(
        self, *, system: str, user: str,
        max_tokens: int = 4096, temperature: float = 0.2,
    ) -> str:
        self.calls.append(_RecordedCall(system, user, max_tokens, temperature))
        if self._fn is not None:
            return self._fn(system=system, user=user,
                            max_tokens=max_tokens, temperature=temperature)
        if not self._queue:
            raise IndexError("FakeLLMClient ran out of scripted responses")
        return self._queue.pop(0)
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `pytest tests/test_llm_fake.py -v`
Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add lib/llm/__init__.py lib/llm/base.py lib/llm/fake.py tests/test_llm_fake.py
git commit -m "feat(llm): LLMClient protocol + FakeLLMClient test double"
```

---

## Task 6: AnthropicClient

**Files:**
- Create: `lib/llm/anthropic_client.py`
- Modify: `lib/llm/__init__.py` (export `AnthropicClient`)
- Test: `tests/test_anthropic_client.py`

**What it does:** A thin wrapper around the `anthropic` SDK that conforms to `LLMClient`. The SDK call is mocked in tests so the test suite never hits the network.

- [ ] **Step 1: Write the failing test in `tests/test_anthropic_client.py`**

```python
from unittest.mock import MagicMock

from lib.llm.anthropic_client import AnthropicClient


def test_anthropic_client_calls_sdk(mocker):
    fake_msg = MagicMock()
    fake_msg.content = [MagicMock(text="hi there")]
    fake_anthropic = MagicMock()
    fake_anthropic.messages.create.return_value = fake_msg
    mocker.patch("lib.llm.anthropic_client.Anthropic",
                 return_value=fake_anthropic)
    c = AnthropicClient(api_key="sk-ant-x", model="m1",
                        default_max_tokens=100, default_temperature=0.1)
    out = c.complete(system="sys", user="usr")
    assert out == "hi there"
    fake_anthropic.messages.create.assert_called_once()
    kwargs = fake_anthropic.messages.create.call_args.kwargs
    assert kwargs["model"] == "m1"
    assert kwargs["system"] == "sys"
    assert kwargs["max_tokens"] == 100
    assert kwargs["temperature"] == 0.1
    assert kwargs["messages"] == [{"role": "user", "content": "usr"}]


def test_anthropic_client_respects_overrides(mocker):
    fake_msg = MagicMock()
    fake_msg.content = [MagicMock(text="ok")]
    fake = MagicMock()
    fake.messages.create.return_value = fake_msg
    mocker.patch("lib.llm.anthropic_client.Anthropic", return_value=fake)
    c = AnthropicClient(api_key="k", model="m", default_max_tokens=10,
                        default_temperature=0.0)
    c.complete(system="s", user="u", max_tokens=999, temperature=0.7)
    kwargs = fake.messages.create.call_args.kwargs
    assert kwargs["max_tokens"] == 999
    assert kwargs["temperature"] == 0.7
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_anthropic_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lib.llm.anthropic_client'`.

- [ ] **Step 3: Implement `lib/llm/anthropic_client.py`**

```python
"""LLMClient backed by the Anthropic SDK."""
from __future__ import annotations

from anthropic import Anthropic


class AnthropicClient:
    def __init__(
        self, *, api_key: str, model: str,
        default_max_tokens: int = 4096, default_temperature: float = 0.2,
    ):
        if not api_key:
            raise ValueError("AnthropicClient requires an API key")
        self._client = Anthropic(api_key=api_key)
        self.model = model
        self.default_max_tokens = default_max_tokens
        self.default_temperature = default_temperature

    def complete(
        self, *, system: str, user: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        msg = self._client.messages.create(
            model=self.model,
            system=system,
            max_tokens=max_tokens if max_tokens is not None else self.default_max_tokens,
            temperature=temperature if temperature is not None else self.default_temperature,
            messages=[{"role": "user", "content": user}],
        )
        # join all text blocks
        return "".join(getattr(b, "text", "") for b in msg.content)
```

- [ ] **Step 4: Update `lib/llm/__init__.py` to export `AnthropicClient`**

```python
from lib.llm.base import LLMClient
from lib.llm.fake import FakeLLMClient
from lib.llm.anthropic_client import AnthropicClient

__all__ = ["LLMClient", "FakeLLMClient", "AnthropicClient"]
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `pytest tests/test_anthropic_client.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add lib/llm/anthropic_client.py lib/llm/__init__.py tests/test_anthropic_client.py
git commit -m "feat(llm): AnthropicClient wrapping the Anthropic SDK"
```

---

## Task 7: ClaudeCodeClient (subprocess)

**Files:**
- Create: `lib/llm/claude_code_client.py`
- Modify: `lib/llm/__init__.py`
- Test: `tests/test_claude_code_client.py`

**What it does:** Calls the `claude` CLI in non-interactive mode (`-p`) so the wiki tasks can run inside Claude Code with skills available. Output is wrapped in `<result>...</result>` tags by the prompt convention so we can robustly extract the answer.

- [ ] **Step 1: Write the failing test in `tests/test_claude_code_client.py`**

```python
from unittest.mock import MagicMock

import pytest

from lib.llm.claude_code_client import ClaudeCodeClient


def test_claude_code_client_invokes_subprocess(mocker):
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = "thinking...\n<result>final answer</result>\nbye\n"
    fake.stderr = ""
    run = mocker.patch("lib.llm.claude_code_client.subprocess.run",
                       return_value=fake)
    c = ClaudeCodeClient(binary="claude")
    out = c.complete(system="be helpful", user="hello")
    assert out == "final answer"
    args, kwargs = run.call_args
    cmd = args[0]
    assert cmd[0] == "claude"
    assert "-p" in cmd
    # combined system+user passed via stdin
    assert kwargs["input"]
    assert "be helpful" in kwargs["input"]
    assert "hello" in kwargs["input"]


def test_claude_code_client_no_result_tag_returns_full_stdout(mocker):
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = "raw answer with no tags"
    fake.stderr = ""
    mocker.patch("lib.llm.claude_code_client.subprocess.run",
                 return_value=fake)
    c = ClaudeCodeClient(binary="claude")
    assert c.complete(system="s", user="u") == "raw answer with no tags"


def test_claude_code_client_raises_on_failure(mocker):
    fake = MagicMock()
    fake.returncode = 2
    fake.stdout = ""
    fake.stderr = "boom"
    mocker.patch("lib.llm.claude_code_client.subprocess.run",
                 return_value=fake)
    c = ClaudeCodeClient(binary="claude")
    with pytest.raises(RuntimeError, match="claude CLI failed"):
        c.complete(system="s", user="u")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_claude_code_client.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `lib/llm/claude_code_client.py`**

```python
"""LLMClient that shells out to the `claude` CLI in non-interactive mode."""
from __future__ import annotations

import re
import subprocess


_RESULT_RE = re.compile(r"<result>(.*?)</result>", re.DOTALL)

_PROMPT_TEMPLATE = """\
{system}

You MUST wrap your final answer in <result>...</result> tags. \
Do not include anything else inside the tags. \
Reasoning, tool use, and explanations may appear outside the tags.

USER REQUEST:
{user}
"""


class ClaudeCodeClient:
    def __init__(self, *, binary: str = "claude"):
        self.binary = binary

    def complete(
        self, *, system: str, user: str,
        max_tokens: int = 4096, temperature: float = 0.2,
    ) -> str:
        prompt = _PROMPT_TEMPLATE.format(system=system, user=user)
        # `claude -p` reads prompt from argv; stdin is also accepted on newer
        # builds. We pass via stdin for robustness (no argv length limits).
        proc = subprocess.run(
            [self.binary, "-p"],
            input=prompt,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"claude CLI failed (rc={proc.returncode}): {proc.stderr.strip()}"
            )
        m = _RESULT_RE.search(proc.stdout)
        return m.group(1).strip() if m else proc.stdout.strip()
```

- [ ] **Step 4: Update `lib/llm/__init__.py`**

```python
from lib.llm.base import LLMClient
from lib.llm.fake import FakeLLMClient
from lib.llm.anthropic_client import AnthropicClient
from lib.llm.claude_code_client import ClaudeCodeClient

__all__ = ["LLMClient", "FakeLLMClient", "AnthropicClient", "ClaudeCodeClient"]
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `pytest tests/test_claude_code_client.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add lib/llm/claude_code_client.py lib/llm/__init__.py tests/test_claude_code_client.py
git commit -m "feat(llm): ClaudeCodeClient shelling out to claude -p"
```

---

## Task 8: PDF parser (PyMuPDF → full.md)

**Files:**
- Create: `lib/ingestion/__init__.py` (empty)
- Create: `lib/ingestion/pdf_parser.py`
- Test: `tests/test_pdf_parser.py`
- Test fixture: generated in test (no binary fixture committed)

**What it does:** Reads a PDF with PyMuPDF, extracts text per page, joins into a single markdown string with simple page separators, and reports whether truncation was applied.

- [ ] **Step 1: Write the failing test in `tests/test_pdf_parser.py`**

```python
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
```

- [ ] **Step 2: Create empty `lib/ingestion/__init__.py`**

```bash
mkdir -p lib/ingestion && touch lib/ingestion/__init__.py
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `pytest tests/test_pdf_parser.py -v`
Expected: FAIL — module missing.

- [ ] **Step 4: Implement `lib/ingestion/pdf_parser.py`**

```python
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
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `pytest tests/test_pdf_parser.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add lib/ingestion/__init__.py lib/ingestion/pdf_parser.py tests/test_pdf_parser.py
git commit -m "feat(ingest): PyMuPDF parser with char-budget truncation"
```

---

## Task 9: Upload fetcher

**Files:**
- Create: `lib/ingestion/fetchers/__init__.py` (empty)
- Create: `lib/ingestion/fetchers/upload.py`
- Test: `tests/test_upload_fetcher.py`

**What it does:** A "fetcher" takes a source spec and returns `FetchedSource` with raw bytes plus minimal metadata (filename, suggested title, source_type). For uploads, the source spec is just a local path.

- [ ] **Step 1: Write the failing test in `tests/test_upload_fetcher.py`**

```python
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
```

- [ ] **Step 2: Create empty `lib/ingestion/fetchers/__init__.py`**

```bash
mkdir -p lib/ingestion/fetchers && touch lib/ingestion/fetchers/__init__.py
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `pytest tests/test_upload_fetcher.py -v`
Expected: FAIL — module missing.

- [ ] **Step 4: Implement `lib/ingestion/fetchers/upload.py`**

```python
"""Fetcher for local PDF files supplied by the user."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FetchedSource:
    raw_bytes: bytes
    suggested_title: str
    source_type: str          # "upload" | "arxiv" | "web" | "search"
    url: Optional[str] = None
    arxiv_id: Optional[str] = None


def upload_fetch(path: Path) -> FetchedSource:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"upload_fetch must be a PDF, got {path.suffix}")
    return FetchedSource(
        raw_bytes=path.read_bytes(),
        suggested_title=path.stem,
        source_type="upload",
    )
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `pytest tests/test_upload_fetcher.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add lib/ingestion/fetchers/__init__.py lib/ingestion/fetchers/upload.py tests/test_upload_fetcher.py
git commit -m "feat(ingest): local PDF upload fetcher"
```

---

## Task 10: Summarization (LLM call producing notes + meta fields)

**Files:**
- Create: `lib/ingestion/summarize.py`
- Test: `tests/test_summarize.py`

**What it does:** Given parsed `full.md` text, the seed taxonomy, and an `LLMClient`, calls the LLM with a strict JSON-output prompt and returns a typed `SummaryResult` containing fields we'll plug into `meta.json` plus the markdown body for `notes.md`.

- [ ] **Step 1: Write the failing test in `tests/test_summarize.py`**

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_summarize.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `lib/ingestion/summarize.py`**

```python
"""LLM-driven summarization: full.md -> SummaryResult."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from lib.llm.base import LLMClient


_SYSTEM = """\
You are an indexing assistant for a research-paper wiki on autonomous driving.
You read a paper's extracted text and emit a strict JSON object describing it.
Be precise, factual, and concise.
"""

_USER_TEMPLATE = """\
Paper text (may be truncated):
---BEGIN PAPER---
{full_md}
---END PAPER---

Available primary categories (pick exactly one of these for primary_category):
{taxonomy_list}

Return ONLY a JSON object with these exact keys:
{{
  "title": str,
  "authors": [str, ...],
  "year": int,
  "primary_category": str,           // MUST be one of the listed categories
  "secondary_categories": [str, ...],
  "keywords": [str, ...],            // 3-8 short keywords
  "one_line_summary": str,           // <= 200 chars, technical, no fluff
  "notes_md": str                    // 300-500 word markdown: Problem, Method, Key Results, Novelty
}}

No prose, no code fences. Just the JSON object.
"""


@dataclass
class SummaryResult:
    title: str
    authors: list[str]
    year: int
    primary_category: str
    secondary_categories: list[str]
    keywords: list[str]
    one_line_summary: str
    notes_md: str


def _strip_code_fences(s: str) -> str:
    s = s.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", s, re.DOTALL)
    return m.group(1).strip() if m else s


def summarize_paper(
    *, full_md: str, seed_taxonomy: list[str], llm: LLMClient,
    max_tokens: int = 4096,
) -> SummaryResult:
    user = _USER_TEMPLATE.format(
        full_md=full_md,
        taxonomy_list="\n".join(f"- {c}" for c in seed_taxonomy),
    )
    raw = llm.complete(system=_SYSTEM, user=user, max_tokens=max_tokens)
    raw = _strip_code_fences(raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON: {e}") from e

    primary = data.get("primary_category", "misc")
    if primary not in seed_taxonomy:
        primary = "misc" if "misc" in seed_taxonomy else seed_taxonomy[-1]

    return SummaryResult(
        title=data["title"],
        authors=list(data.get("authors", [])),
        year=int(data["year"]),
        primary_category=primary,
        secondary_categories=list(data.get("secondary_categories", [])),
        keywords=list(data.get("keywords", [])),
        one_line_summary=data["one_line_summary"],
        notes_md=data["notes_md"],
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_summarize.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add lib/ingestion/summarize.py tests/test_summarize.py
git commit -m "feat(ingest): LLM summarization producing SummaryResult"
```

---

## Task 11: Ingestion orchestrator (end-to-end PDF → papers/<id>/)

**Files:**
- Create: `lib/ingestion/orchestrator.py`
- Test: `tests/test_ingestion_orchestrator.py`

**What it does:** Takes a `FetchedSource`, runs the parser and summarizer, allocates a `paper_id`, writes `source.pdf`, `full.md`, `notes.md`, and `meta.json`. Idempotent: if a paper with the same `content_hash` already exists, returns its existing `paper_id` with `created=False`. Does NOT touch `wiki/` (that's the indexing module's job — we'll wire it up in Task 14).

- [ ] **Step 1: Write the failing test in `tests/test_ingestion_orchestrator.py`**

```python
import json
from pathlib import Path

import fitz
import pytest

from lib.ingestion.orchestrator import ingest_pdf
from lib.ingestion.fetchers.upload import FetchedSource
from lib.llm.fake import FakeLLMClient
from lib.storage import PaperStorage


def make_pdf(path: Path, text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()
    return path.read_bytes()


SUMMARY_JSON = json.dumps({
    "title": "Sample VLA Paper",
    "authors": ["Alice"],
    "year": 2025,
    "primary_category": "vla",
    "secondary_categories": [],
    "keywords": ["vla", "driving"],
    "one_line_summary": "VLA for driving.",
    "notes_md": "## Method\nA VLA.\n",
})


def make_fetched(tmp_path: Path) -> FetchedSource:
    pdf = tmp_path / "Sample VLA Paper.pdf"
    raw = make_pdf(pdf, "Hello VLA")
    return FetchedSource(
        raw_bytes=raw,
        suggested_title="Sample VLA Paper",
        source_type="upload",
    )


def test_ingest_pdf_creates_paper(tmp_path):
    storage = PaperStorage(tmp_path)
    fetched = make_fetched(tmp_path)
    fake = FakeLLMClient(responses=[SUMMARY_JSON])
    result = ingest_pdf(
        fetched=fetched, storage=storage,
        seed_taxonomy=["vla", "misc"], llm=fake, max_full_md_chars=10000,
    )
    assert result.created is True
    assert result.paper_id.startswith("2025-")
    pdir = storage.paper_dir(result.paper_id)
    assert (pdir / "source.pdf").exists()
    assert (pdir / "full.md").exists()
    assert (pdir / "notes.md").read_text().startswith("## Method")
    meta = storage.read_meta(result.paper_id)
    assert meta.title == "Sample VLA Paper"
    assert meta.primary_category == "vla"
    assert meta.notes_status == "ok"
    assert meta.source_type == "upload"


def test_ingest_pdf_is_idempotent_on_hash(tmp_path):
    storage = PaperStorage(tmp_path)
    fetched = make_fetched(tmp_path)
    fake1 = FakeLLMClient(responses=[SUMMARY_JSON])
    r1 = ingest_pdf(fetched=fetched, storage=storage,
                    seed_taxonomy=["vla", "misc"], llm=fake1,
                    max_full_md_chars=10000)
    fake2 = FakeLLMClient(responses=[SUMMARY_JSON])  # would be a 2nd call
    r2 = ingest_pdf(fetched=fetched, storage=storage,
                    seed_taxonomy=["vla", "misc"], llm=fake2,
                    max_full_md_chars=10000)
    assert r1.paper_id == r2.paper_id
    assert r2.created is False
    assert len(fake2.calls) == 0  # short-circuited before LLM


def test_ingest_pdf_marks_truncation(tmp_path):
    storage = PaperStorage(tmp_path)
    fetched = make_fetched(tmp_path)
    fake = FakeLLMClient(responses=[SUMMARY_JSON])
    result = ingest_pdf(
        fetched=fetched, storage=storage,
        seed_taxonomy=["vla", "misc"], llm=fake,
        max_full_md_chars=5,  # forces truncation
    )
    meta = storage.read_meta(result.paper_id)
    assert meta.full_md_truncated is True
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_ingestion_orchestrator.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `lib/ingestion/orchestrator.py`**

```python
"""Orchestrate: fetched bytes -> parsed text -> LLM summary -> papers/<id>/."""
from __future__ import annotations

import datetime as dt
import tempfile
from pathlib import Path

from lib.ingestion.fetchers.upload import FetchedSource
from lib.ingestion.pdf_parser import parse_pdf
from lib.ingestion.summarize import summarize_paper
from lib.llm.base import LLMClient
from lib.models import IngestResult, PaperMeta
from lib.storage import PaperStorage, allocate_paper_id, content_hash


def _utcnow_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ingest_pdf(
    *,
    fetched: FetchedSource,
    storage: PaperStorage,
    seed_taxonomy: list[str],
    llm: LLMClient,
    max_full_md_chars: int,
) -> IngestResult:
    h = content_hash(fetched.raw_bytes)
    existing = storage.find_by_hash(h)
    if existing is not None:
        return IngestResult(paper_id=existing, created=False,
                            message=f"already ingested as {existing}")

    # write PDF to a temp file for PyMuPDF (it wants a path)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(fetched.raw_bytes)
        tmp_path = Path(tmp.name)
    try:
        parsed = parse_pdf(tmp_path, max_chars=max_full_md_chars)
    finally:
        tmp_path.unlink(missing_ok=True)

    summary = summarize_paper(
        full_md=parsed.text, seed_taxonomy=seed_taxonomy, llm=llm,
    )

    paper_id = allocate_paper_id(
        storage, year=summary.year, slug_hint=summary.title,
    )
    pdir = storage.paper_dir(paper_id)
    pdir.mkdir(parents=True, exist_ok=False)
    (pdir / "source.pdf").write_bytes(fetched.raw_bytes)
    (pdir / "full.md").write_text(parsed.text)
    (pdir / "notes.md").write_text(summary.notes_md)

    meta = PaperMeta(
        paper_id=paper_id,
        title=summary.title,
        authors=summary.authors,
        year=summary.year,
        arxiv_id=fetched.arxiv_id,
        url=fetched.url,
        keywords=summary.keywords,
        primary_category=summary.primary_category,
        secondary_categories=summary.secondary_categories,
        ingested_at=_utcnow_iso(),
        source_type=fetched.source_type,  # type: ignore[arg-type]
        content_hash=h,
        one_line_summary=summary.one_line_summary,
        notes_status="ok",
        full_md_truncated=parsed.truncated,
    )
    storage.write_meta(meta)
    return IngestResult(paper_id=paper_id, created=True,
                        message=f"ingested {paper_id}")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_ingestion_orchestrator.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add lib/ingestion/orchestrator.py tests/test_ingestion_orchestrator.py
git commit -m "feat(ingest): orchestrator wiring fetcher+parser+summarizer to disk"
```

---

## Task 12: Indexing — wiki writer

**Files:**
- Create: `lib/indexing/__init__.py` (empty)
- Create: `lib/indexing/writer.py`
- Test: `tests/test_indexing_writer.py`

**What it does:** Appends or replaces a paper's row in `wiki/index.md` (the master pipe-table) and in the appropriate `wiki/categories/<cat>.md` file. Creates files with their headers if missing.

- [ ] **Step 1: Write the failing test in `tests/test_indexing_writer.py`**

```python
from pathlib import Path

import pytest

from lib.indexing.writer import upsert_paper_in_wiki, WikiPaths
from lib.models import PaperMeta


def make_meta(pid="2024-x", year=2024, cat="vla", summary="s",
              keywords=("k1", "k2"), title="A Title") -> PaperMeta:
    return PaperMeta(
        paper_id=pid, title=title, authors=[], year=year,
        primary_category=cat, ingested_at="2026-05-02T00:00:00Z",
        source_type="upload", content_hash="h",
        keywords=list(keywords),
        one_line_summary=summary, notes_status="ok",
    )


def test_creates_index_and_category_file(tmp_path):
    paths = WikiPaths(tmp_path / "wiki")
    upsert_paper_in_wiki(make_meta(), paths)
    idx = (tmp_path / "wiki" / "index.md").read_text()
    cat = (tmp_path / "wiki" / "categories" / "vla.md").read_text()
    assert "| paper_id |" in idx  # header present
    assert "| 2024-x | 2024 | A Title | vla | s | k1, k2 |" in idx
    assert "# vla" in cat
    assert "2024-x" in cat


def test_idempotent_upsert(tmp_path):
    paths = WikiPaths(tmp_path / "wiki")
    upsert_paper_in_wiki(make_meta(), paths)
    upsert_paper_in_wiki(make_meta(summary="updated"), paths)
    idx = (tmp_path / "wiki" / "index.md").read_text()
    # only one row for 2024-x
    assert idx.count("| 2024-x |") == 1
    assert "updated" in idx
    assert "| s |" not in idx


def test_two_papers_same_category(tmp_path):
    paths = WikiPaths(tmp_path / "wiki")
    upsert_paper_in_wiki(make_meta(pid="2024-a"), paths)
    upsert_paper_in_wiki(make_meta(pid="2024-b"), paths)
    cat = (tmp_path / "wiki" / "categories" / "vla.md").read_text()
    assert "2024-a" in cat
    assert "2024-b" in cat


def test_recategorize_removes_from_old_category(tmp_path):
    paths = WikiPaths(tmp_path / "wiki")
    upsert_paper_in_wiki(make_meta(pid="2024-x", cat="vla"), paths)
    upsert_paper_in_wiki(make_meta(pid="2024-x", cat="world_model"), paths)
    vla = (tmp_path / "wiki" / "categories" / "vla.md").read_text()
    wm = (tmp_path / "wiki" / "categories" / "world_model.md").read_text()
    assert "2024-x" not in vla
    assert "2024-x" in wm
```

- [ ] **Step 2: Create empty `lib/indexing/__init__.py`**

```bash
mkdir -p lib/indexing && touch lib/indexing/__init__.py
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `pytest tests/test_indexing_writer.py -v`
Expected: FAIL — module missing.

- [ ] **Step 4: Implement `lib/indexing/writer.py`**

```python
"""Write/update wiki/index.md and wiki/categories/<cat>.md."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lib.models import PaperMeta


_INDEX_HEADER = (
    "| paper_id | year | title | primary_category | one_line_summary | keywords |\n"
    "|----------|------|-------|------------------|------------------|----------|\n"
)


@dataclass
class WikiPaths:
    root: Path

    @property
    def index_md(self) -> Path:
        return self.root / "index.md"

    @property
    def categories_dir(self) -> Path:
        return self.root / "categories"

    def category_md(self, cat: str) -> Path:
        return self.categories_dir / f"{cat}.md"


def _index_row(m: PaperMeta) -> str:
    kws = ", ".join(m.keywords)
    return f"| {m.paper_id} | {m.year} | {m.title} | {m.primary_category} | {m.one_line_summary} | {kws} |\n"


def _category_entry(m: PaperMeta) -> str:
    return (
        f"## {m.paper_id} — {m.title}\n"
        f"- Year: {m.year}\n"
        f"- Summary: {m.one_line_summary}\n"
        f"- Keywords: {', '.join(m.keywords)}\n"
        f"- Notes: ../../papers/{m.paper_id}/notes.md\n\n"
    )


def _ensure_index(paths: WikiPaths) -> None:
    paths.root.mkdir(parents=True, exist_ok=True)
    if not paths.index_md.exists():
        paths.index_md.write_text(_INDEX_HEADER)


def _ensure_category(paths: WikiPaths, cat: str) -> None:
    paths.categories_dir.mkdir(parents=True, exist_ok=True)
    cat_path = paths.category_md(cat)
    if not cat_path.exists():
        cat_path.write_text(f"# {cat}\n\nPapers categorized as `{cat}`.\n\n")


def _remove_paper_from_index(text: str, paper_id: str) -> str:
    return "".join(
        line for line in text.splitlines(keepends=True)
        if not line.startswith(f"| {paper_id} |")
    )


def _remove_paper_from_category(text: str, paper_id: str) -> str:
    # An entry starts with "## <paper_id> —" and ends at the next "## " or EOF.
    pattern = re.compile(
        rf"(^## {re.escape(paper_id)} — .*?(?=^## |\Z))",
        re.DOTALL | re.MULTILINE,
    )
    return pattern.sub("", text)


def upsert_paper_in_wiki(meta: PaperMeta, paths: WikiPaths) -> None:
    _ensure_index(paths)
    # 1) update master index
    cur = paths.index_md.read_text()
    cur = _remove_paper_from_index(cur, meta.paper_id)
    if not cur.endswith("\n"):
        cur += "\n"
    cur += _index_row(meta)
    paths.index_md.write_text(cur)

    # 2) remove from any old category file (cheap scan)
    if paths.categories_dir.exists():
        for cat_file in paths.categories_dir.glob("*.md"):
            if cat_file.name == f"{meta.primary_category}.md":
                continue
            text = cat_file.read_text()
            new = _remove_paper_from_category(text, meta.paper_id)
            if new != text:
                cat_file.write_text(new)

    # 3) write into target category file
    _ensure_category(paths, meta.primary_category)
    cat_path = paths.category_md(meta.primary_category)
    text = cat_path.read_text()
    text = _remove_paper_from_category(text, meta.paper_id)
    if not text.endswith("\n\n"):
        text = text.rstrip() + "\n\n"
    text += _category_entry(meta)
    cat_path.write_text(text)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `pytest tests/test_indexing_writer.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add lib/indexing/__init__.py lib/indexing/writer.py tests/test_indexing_writer.py
git commit -m "feat(indexing): upsert paper into master index + category file"
```

---

## Task 13: Indexing — rebuild from meta.json files

**Files:**
- Create: `lib/indexing/rebuild.py`
- Test: `tests/test_indexing_rebuild.py`

**What it does:** Wipes `wiki/` and regenerates it from scratch by iterating over every `papers/*/meta.json`. Used as a disaster-recovery path and during rebalance (Plan 2).

- [ ] **Step 1: Write the failing test in `tests/test_indexing_rebuild.py`**

```python
from pathlib import Path

from lib.indexing.rebuild import rebuild_wiki
from lib.indexing.writer import WikiPaths
from lib.storage import PaperStorage
from lib.models import PaperMeta


def write_paper(storage, pid, cat="vla", year=2024):
    storage.paper_dir(pid).mkdir(parents=True)
    storage.write_meta(PaperMeta(
        paper_id=pid, title=f"T-{pid}", authors=[], year=year,
        primary_category=cat, ingested_at="2026-05-02T00:00:00Z",
        source_type="upload", content_hash=pid,
        one_line_summary=f"summary {pid}", notes_status="ok",
    ))


def test_rebuild_creates_wiki_from_metas(tmp_path):
    storage = PaperStorage(tmp_path)
    write_paper(storage, "2024-a", cat="vla")
    write_paper(storage, "2024-b", cat="world_model")
    paths = WikiPaths(tmp_path / "wiki")
    rebuild_wiki(storage, paths, seed_taxonomy=["vla", "world_model", "misc"])
    idx = paths.index_md.read_text()
    assert "2024-a" in idx and "2024-b" in idx
    assert "2024-a" in paths.category_md("vla").read_text()
    assert "2024-b" in paths.category_md("world_model").read_text()
    # seed taxonomy categories all exist as files (even if empty)
    assert paths.category_md("misc").exists()


def test_rebuild_overwrites_old_state(tmp_path):
    storage = PaperStorage(tmp_path)
    write_paper(storage, "2024-a", cat="vla")
    paths = WikiPaths(tmp_path / "wiki")
    paths.root.mkdir()
    paths.index_md.write_text("STALE CONTENT\n| 9999-zombie |\n")
    rebuild_wiki(storage, paths, seed_taxonomy=["vla", "misc"])
    idx = paths.index_md.read_text()
    assert "STALE" not in idx
    assert "9999-zombie" not in idx
    assert "2024-a" in idx
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_indexing_rebuild.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `lib/indexing/rebuild.py`**

```python
"""Regenerate wiki/ from papers/*/meta.json. Source of truth = meta.json."""
from __future__ import annotations

import shutil

from lib.indexing.writer import WikiPaths, upsert_paper_in_wiki, _ensure_category, _ensure_index
from lib.storage import PaperStorage


def rebuild_wiki(
    storage: PaperStorage, paths: WikiPaths, *, seed_taxonomy: list[str],
) -> int:
    if paths.root.exists():
        shutil.rmtree(paths.root)
    _ensure_index(paths)
    for cat in seed_taxonomy:
        _ensure_category(paths, cat)
    count = 0
    for meta in storage.iter_metas():
        upsert_paper_in_wiki(meta, paths)
        count += 1
    return count
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_indexing_rebuild.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add lib/indexing/rebuild.py tests/test_indexing_rebuild.py
git commit -m "feat(indexing): rebuild wiki from meta.json source-of-truth"
```

---

## Task 14: Query — pass 1 routing

**Files:**
- Create: `lib/query/__init__.py` (empty)
- Create: `lib/query/route.py`
- Test: `tests/test_query_route.py`

**What it does:** Given the user's question and the contents of `wiki/index.md` (and optionally `taxonomy.md`), asks the LLM to return a JSON list of `paper_id`s that look most relevant. Capped at `max_papers`.

- [ ] **Step 1: Write the failing test in `tests/test_query_route.py`**

```python
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
```

- [ ] **Step 2: Create empty `lib/query/__init__.py`**

```bash
mkdir -p lib/query && touch lib/query/__init__.py
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `pytest tests/test_query_route.py -v`
Expected: FAIL — module missing.

- [ ] **Step 4: Implement `lib/query/route.py`**

```python
"""Pass 1: pick relevant paper_ids from the wiki index given a question."""
from __future__ import annotations

import json
import re

from lib.llm.base import LLMClient


_SYSTEM = """\
You are a routing assistant for a research-paper wiki. \
Given the user's question and the wiki index, return the paper_ids \
most likely to help answer the question. Be selective.\
"""

_USER_TEMPLATE = """\
USER QUESTION:
{question}

WIKI INDEX (one row per paper):
{index_md}

Return ONLY a JSON object of the form: {{"paper_ids": ["id1", "id2", ...]}}.
Pick at most {max_papers} ids. If nothing in the index seems relevant, \
return {{"paper_ids": []}}.
"""

_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)
_ROW_ID_RE = re.compile(r"^\|\s*([^\s|]+)\s*\|", re.MULTILINE)


def _known_ids(index_md: str) -> set[str]:
    ids = set(_ROW_ID_RE.findall(index_md))
    ids.discard("paper_id")  # header
    ids.discard("----------")  # separator
    return ids


def route_query(
    *, question: str, index_md: str, llm: LLMClient, max_papers: int = 5,
) -> list[str]:
    user = _USER_TEMPLATE.format(
        question=question, index_md=index_md, max_papers=max_papers,
    )
    raw = llm.complete(system=_SYSTEM, user=user)
    raw = raw.strip()
    m = _FENCE_RE.match(raw)
    if m:
        raw = m.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    ids = data.get("paper_ids", []) or []
    known = _known_ids(index_md)
    filtered = [pid for pid in ids if pid in known]
    return filtered[:max_papers]
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `pytest tests/test_query_route.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add lib/query/__init__.py lib/query/route.py tests/test_query_route.py
git commit -m "feat(query): pass-1 LLM routing over wiki index"
```

---

## Task 15: Query — pass 2 answering

**Files:**
- Create: `lib/query/answer.py`
- Test: `tests/test_query_answer.py`

**What it does:** Given the user's question and the `notes.md` of the routed papers, produces a final natural-language answer with `[paper_id]` citations.

- [ ] **Step 1: Write the failing test in `tests/test_query_answer.py`**

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_query_answer.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `lib/query/answer.py`**

```python
"""Pass 2: synthesize an answer from per-paper notes."""
from __future__ import annotations

import re
from dataclasses import dataclass

from lib.llm.base import LLMClient


_SYSTEM = """\
You answer technical questions about autonomous-driving research papers \
using ONLY the per-paper notes provided. Cite each claim with the \
paper_id in square brackets, e.g. [2024-a]. If the notes do not contain \
the answer, say so directly.\
"""

_USER_TEMPLATE = """\
USER QUESTION:
{question}

PAPER NOTES (one block per paper):
{blocks}

Answer the question, citing paper_ids in [brackets].
"""

_CITE_RE = re.compile(r"\[([A-Za-z0-9][A-Za-z0-9_\-]*)\]")


@dataclass
class AnswerResult:
    answer: str
    cited_paper_ids: list[str]


def answer_from_notes(
    *, question: str, notes_by_id: dict[str, str], llm: LLMClient,
    max_tokens: int = 2048,
) -> AnswerResult:
    if not notes_by_id:
        return AnswerResult(
            answer="No library hit. The wiki has no relevant entries for this question.",
            cited_paper_ids=[],
        )
    blocks = "\n\n".join(
        f"[{pid}]\n{notes}" for pid, notes in notes_by_id.items()
    )
    user = _USER_TEMPLATE.format(question=question, blocks=blocks)
    text = llm.complete(system=_SYSTEM, user=user, max_tokens=max_tokens)
    cited = []
    for m in _CITE_RE.finditer(text):
        pid = m.group(1)
        if pid in notes_by_id and pid not in cited:
            cited.append(pid)
    return AnswerResult(answer=text, cited_paper_ids=cited)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_query_answer.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add lib/query/answer.py tests/test_query_answer.py
git commit -m "feat(query): pass-2 answer synthesis with citation extraction"
```

---

## Task 16: Query orchestrator

**Files:**
- Create: `lib/query/orchestrator.py`
- Test: `tests/test_query_orchestrator.py`

**What it does:** End-to-end: read `wiki/index.md` → call `route_query` → load `notes.md` for each picked paper → call `answer_from_notes` → return combined result.

- [ ] **Step 1: Write the failing test in `tests/test_query_orchestrator.py`**

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_query_orchestrator.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `lib/query/orchestrator.py`**

```python
"""Two-pass query: route over wiki/index.md, then answer from notes.md."""
from __future__ import annotations

from dataclasses import dataclass

from lib.indexing.writer import WikiPaths
from lib.llm.base import LLMClient
from lib.query.answer import answer_from_notes
from lib.query.route import route_query
from lib.storage import PaperStorage


@dataclass
class QueryResult:
    answer: str
    routed_paper_ids: list[str]
    cited_paper_ids: list[str]


def query_wiki(
    *, question: str, storage: PaperStorage, wiki_paths: WikiPaths,
    llm: LLMClient, max_papers: int = 5,
) -> QueryResult:
    if not wiki_paths.index_md.exists():
        return QueryResult(
            answer="No library hit. The wiki has no entries yet.",
            routed_paper_ids=[], cited_paper_ids=[],
        )
    index_md = wiki_paths.index_md.read_text()
    routed = route_query(question=question, index_md=index_md,
                         llm=llm, max_papers=max_papers)
    if not routed:
        ar = answer_from_notes(question=question, notes_by_id={}, llm=llm)
        return QueryResult(answer=ar.answer, routed_paper_ids=[],
                           cited_paper_ids=[])
    notes_by_id: dict[str, str] = {}
    for pid in routed:
        np = storage.notes_md_path(pid)
        if np.exists():
            notes_by_id[pid] = np.read_text()
    ar = answer_from_notes(question=question, notes_by_id=notes_by_id, llm=llm)
    return QueryResult(
        answer=ar.answer, routed_paper_ids=routed,
        cited_paper_ids=ar.cited_paper_ids,
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_query_orchestrator.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add lib/query/orchestrator.py tests/test_query_orchestrator.py
git commit -m "feat(query): end-to-end two-pass query orchestrator"
```

---

## Task 17: Wire ingestion → indexing in a thin façade

**Files:**
- Modify: `lib/__init__.py` to export `ingest_pdf_and_index`
- Create: `lib/pipeline.py`
- Test: `tests/test_pipeline.py`

**What it does:** A small façade so the CLI/UI don't have to know that ingestion and indexing are two separate modules. Calls `ingest_pdf` then, if `created`, `upsert_paper_in_wiki`. This is the only place `ingestion` and `indexing` are mentioned together.

- [ ] **Step 1: Write the failing test in `tests/test_pipeline.py`**

```python
import json
from pathlib import Path

import fitz

from lib.pipeline import ingest_pdf_and_index
from lib.indexing.writer import WikiPaths
from lib.ingestion.fetchers.upload import FetchedSource
from lib.llm.fake import FakeLLMClient
from lib.storage import PaperStorage


def make_pdf_bytes(tmp_path: Path) -> bytes:
    p = tmp_path / "p.pdf"
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "hello")
    doc.save(str(p))
    doc.close()
    return p.read_bytes()


SUMMARY = json.dumps({
    "title": "T", "authors": [], "year": 2024,
    "primary_category": "vla", "secondary_categories": [],
    "keywords": ["k"], "one_line_summary": "s",
    "notes_md": "n",
})


def test_pipeline_ingests_and_indexes(tmp_path):
    storage = PaperStorage(tmp_path)
    paths = WikiPaths(tmp_path / "wiki")
    fetched = FetchedSource(
        raw_bytes=make_pdf_bytes(tmp_path),
        suggested_title="T", source_type="upload",
    )
    fake = FakeLLMClient(responses=[SUMMARY])
    result = ingest_pdf_and_index(
        fetched=fetched, storage=storage, wiki_paths=paths,
        seed_taxonomy=["vla", "misc"], llm=fake, max_full_md_chars=10000,
    )
    assert result.created is True
    assert "| 2024-t |" in paths.index_md.read_text()
    assert "2024-t" in paths.category_md("vla").read_text()


def test_pipeline_skips_index_on_duplicate(tmp_path):
    storage = PaperStorage(tmp_path)
    paths = WikiPaths(tmp_path / "wiki")
    fetched = FetchedSource(
        raw_bytes=make_pdf_bytes(tmp_path),
        suggested_title="T", source_type="upload",
    )
    fake = FakeLLMClient(responses=[SUMMARY])
    ingest_pdf_and_index(
        fetched=fetched, storage=storage, wiki_paths=paths,
        seed_taxonomy=["vla", "misc"], llm=fake, max_full_md_chars=10000,
    )
    before = paths.index_md.read_text()
    fake2 = FakeLLMClient(responses=[SUMMARY])
    r2 = ingest_pdf_and_index(
        fetched=fetched, storage=storage, wiki_paths=paths,
        seed_taxonomy=["vla", "misc"], llm=fake2, max_full_md_chars=10000,
    )
    after = paths.index_md.read_text()
    assert r2.created is False
    assert before == after
    assert len(fake2.calls) == 0
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `lib/pipeline.py`**

```python
"""Thin façade combining ingestion + indexing for the CLI/UI."""
from __future__ import annotations

from lib.indexing.writer import WikiPaths, upsert_paper_in_wiki
from lib.ingestion.fetchers.upload import FetchedSource
from lib.ingestion.orchestrator import ingest_pdf
from lib.llm.base import LLMClient
from lib.models import IngestResult
from lib.storage import PaperStorage


def ingest_pdf_and_index(
    *,
    fetched: FetchedSource,
    storage: PaperStorage,
    wiki_paths: WikiPaths,
    seed_taxonomy: list[str],
    llm: LLMClient,
    max_full_md_chars: int,
) -> IngestResult:
    result = ingest_pdf(
        fetched=fetched, storage=storage,
        seed_taxonomy=seed_taxonomy, llm=llm,
        max_full_md_chars=max_full_md_chars,
    )
    if result.created:
        meta = storage.read_meta(result.paper_id)
        upsert_paper_in_wiki(meta, wiki_paths)
    return result
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_pipeline.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add lib/pipeline.py tests/test_pipeline.py
git commit -m "feat(pipeline): façade combining ingest_pdf + wiki upsert"
```

---

## Task 18: CLI

**Files:**
- Create: `cli.py`
- Test: `tests/test_cli.py`

**What it does:** A single `argparse` entrypoint exposing `ingest`, `query`, and `rebuild-index` subcommands. The CLI builds an `LLMClient` based on config and delegates to `lib.pipeline`, `lib.query.orchestrator`, `lib.indexing.rebuild`. No domain logic in `cli.py` itself.

- [ ] **Step 1: Write the failing test in `tests/test_cli.py`**

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL — `cli` module missing or `_make_llm_client` not found.

- [ ] **Step 3: Implement `cli.py`**

```python
"""argparse CLI: ingest, query, rebuild-index."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib.config import Config, load_config
from lib.indexing.rebuild import rebuild_wiki
from lib.indexing.writer import WikiPaths
from lib.ingestion.fetchers.upload import upload_fetch
from lib.llm.base import LLMClient
from lib.pipeline import ingest_pdf_and_index
from lib.query.orchestrator import query_wiki
from lib.storage import PaperStorage


def _make_llm_client(cfg: Config, backend: str | None) -> LLMClient:
    backend = backend or cfg.llm.default_backend
    if backend == "anthropic":
        if not cfg.anthropic_api_key:
            raise SystemExit("ANTHROPIC_API_KEY not set")
        from lib.llm.anthropic_client import AnthropicClient
        return AnthropicClient(
            api_key=cfg.anthropic_api_key,
            model=cfg.llm.anthropic.model,
            default_max_tokens=cfg.llm.anthropic.max_tokens,
            default_temperature=cfg.llm.anthropic.temperature,
        )
    if backend == "claude_code":
        from lib.llm.claude_code_client import ClaudeCodeClient
        return ClaudeCodeClient(binary=cfg.llm.claude_code.binary)
    raise SystemExit(f"unknown backend: {backend}")


def _wiki_paths(cfg: Config) -> WikiPaths:
    return WikiPaths(cfg.data_dir / "wiki")


def _storage(cfg: Config) -> PaperStorage:
    return PaperStorage(cfg.data_dir)


def cmd_ingest(args, cfg: Config) -> int:
    fetched = upload_fetch(Path(args.path))
    llm = _make_llm_client(cfg, args.backend)
    result = ingest_pdf_and_index(
        fetched=fetched, storage=_storage(cfg), wiki_paths=_wiki_paths(cfg),
        seed_taxonomy=cfg.seed_taxonomy, llm=llm,
        max_full_md_chars=cfg.ingest.max_full_md_chars,
    )
    print(result.message)
    return 0


def cmd_query(args, cfg: Config) -> int:
    llm = _make_llm_client(cfg, args.backend)
    out = query_wiki(
        question=args.question, storage=_storage(cfg),
        wiki_paths=_wiki_paths(cfg), llm=llm, max_papers=args.max_papers,
    )
    print(out.answer)
    if out.cited_paper_ids:
        print("\nCited:", ", ".join(out.cited_paper_ids))
    return 0


def cmd_rebuild_index(args, cfg: Config) -> int:
    n = rebuild_wiki(
        _storage(cfg), _wiki_paths(cfg),
        seed_taxonomy=cfg.seed_taxonomy,
    )
    print(f"rebuilt wiki from {n} papers")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="personal_library")
    p.add_argument("--backend", default=None,
                   help="override llm backend (anthropic|claude_code)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("ingest", help="ingest a local PDF")
    pi.add_argument("path")
    pi.set_defaults(func=cmd_ingest)

    pq = sub.add_parser("query", help="query the wiki")
    pq.add_argument("question")
    pq.add_argument("--max-papers", type=int, default=5)
    pq.set_defaults(func=cmd_query)

    pr = sub.add_parser("rebuild-index",
                        help="regenerate wiki/ from papers/*/meta.json")
    pr.set_defaults(func=cmd_rebuild_index)

    args = p.parse_args(argv)
    cfg = load_config()
    return args.func(args, cfg)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: 3 passed.

- [ ] **Step 5: Run the entire test suite to verify no regressions**

Run: `pytest -v`
Expected: ALL passed (~40+ tests).

- [ ] **Step 6: Commit**

```bash
git add cli.py tests/test_cli.py
git commit -m "feat(cli): ingest, query, rebuild-index subcommands"
```

---

## Task 19: Smoke test against a real Anthropic API call (manual)

**Files:**
- Create: `docs/smoke-test.md`

**What it does:** Documents the manual smoke test the developer should run before declaring Plan 1 complete. Not automated because it requires a live API key.

- [ ] **Step 1: Write `docs/smoke-test.md`**

```markdown
# Smoke Test — Plan 1 Acceptance

Run after all unit tests pass. Requires `ANTHROPIC_API_KEY` in `.env`.

## Setup
\`\`\`bash
conda activate personal_library
cp .env.example .env  # then add real key
\`\`\`

## 1. Ingest a real paper
Download any 1-page or short autonomous-driving paper PDF (e.g. an
arXiv abstract printed to PDF). Then:

\`\`\`bash
python cli.py ingest path/to/paper.pdf
\`\`\`

Expected:
- prints `ingested 2024-<slug>` (or similar)
- `data/papers/2024-<slug>/` contains source.pdf, full.md, notes.md, meta.json
- `data/wiki/index.md` has a row for the paper
- `data/wiki/categories/<category>.md` mentions the paper

## 2. Query the wiki
\`\`\`bash
python cli.py query "summarize what's in my library"
\`\`\`

Expected:
- prints a paragraph mentioning the paper
- prints `Cited: 2024-<slug>` line

## 3. Disaster recovery
\`\`\`bash
echo "CORRUPT" > data/wiki/index.md
python cli.py rebuild-index
\`\`\`

Expected:
- prints `rebuilt wiki from N papers`
- `data/wiki/index.md` is restored

## 4. Idempotent ingestion
Re-run step 1 with the same PDF.
Expected: prints `already ingested as <id>`; no LLM call made.
```

- [ ] **Step 2: Commit**

```bash
git add docs/smoke-test.md
git commit -m "docs: manual smoke-test acceptance procedure for Plan 1"
```

---

## Self-Review

**Spec coverage check (against `2026-05-02-personal-library-llm-wiki-design.md`):**
- §3 Architecture, 5 modules with strict boundaries → Tasks 5–17 implement each module; Task 17 is the only place ingestion and indexing meet (the façade).
- §4 On-disk layout → Task 4 (`PaperStorage`), Task 12 (wiki paths), Task 13 (rebuild).
- §5.1 Ingestion flow → Tasks 8 (parse), 9 (upload fetcher), 10 (summarize), 11 (orchestrate). arXiv/web/search fetchers are explicitly Plan 2.
- §5.2 Two-pass query → Tasks 14 (route), 15 (answer), 16 (orchestrator).
- §5.3 Rebalance → deferred to Plan 2 (acknowledged in plan goal).
- §6 LLMClient interface → Tasks 5 (protocol + fake), 6 (Anthropic), 7 (Claude Code).
- §7 Streamlit UI → deferred to Plan 2.
- §8 Configuration → Task 2.
- §9 Conda env → Task 1.
- §10 Error handling: idempotent ingest (Task 11), `meta.json` as source of truth + rebuild (Task 13), notes_status field (Task 3 model).
- §11 Testing strategy: every task is TDD; `FakeLLMClient` is used everywhere; no live network in any unit test.

**Placeholder scan:** No "TBD", "TODO", "implement later", or unspecified test code. Every step contains complete code. ✅

**Type consistency:** `LLMClient.complete` signature is identical across `base.py`, `fake.py`, `anthropic_client.py`, `claude_code_client.py`. `WikiPaths`, `PaperStorage`, `PaperMeta`, `IngestResult`, `QueryResult`, `AnswerResult`, `SummaryResult`, `ParseResult`, `FetchedSource` are each defined once and consumed everywhere. `seed_taxonomy: list[str]` everywhere. `paper_id` strings everywhere. ✅

**Scope check:** This plan = working software at the end (CLI tool that ingests PDFs and answers queries). Out-of-scope items (arXiv/web/search fetchers, rebalance, Streamlit UI) are deferred to Plan 2 and called out in the goal/architecture statement. ✅

---

## End State of Plan 1

After Task 19, the developer has:
- A working conda env `personal_library`.
- `python cli.py ingest paper.pdf` populates `data/papers/<id>/` and updates `data/wiki/`.
- `python cli.py query "..."` returns a cited answer using two-pass routing.
- `python cli.py rebuild-index` regenerates the wiki from `meta.json` files.
- A test suite of ~40 tests, all passing, no live network calls.
- Two LLM backends wired up: Anthropic API and Claude Code subprocess.

Plan 2 will add: arXiv fetcher, web fetcher, search-API fetcher, scheduled keyword search, manual rebalance with diff/confirm, and the Streamlit UI (chat / ingest / wiki browser / maintain).
