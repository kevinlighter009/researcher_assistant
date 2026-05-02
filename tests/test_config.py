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
