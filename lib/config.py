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
