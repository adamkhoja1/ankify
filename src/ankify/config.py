"""Global LLM configuration (provider, model, reasoning effort, API key).

Stored at ~/.config/ankify/config.json (XDG-aware) so it's set once for all projects. The API
key is saved here (home directory, never in a repo); env vars (OPENAI_API_KEY /
ANTHROPIC_API_KEY) are the fallback when no key is configured.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

Provider = Literal["openai", "anthropic"]


class ModelConfig(BaseModel):
    provider: Provider = "openai"
    model: str = "gpt-5.5"
    reasoning_effort: str = "high"  # OpenAI reasoning effort; ignored by the Anthropic path
    api_key: str = ""

    def resolved_key(self) -> str:
        if self.api_key:
            return self.api_key
        env_var = "OPENAI_API_KEY" if self.provider == "openai" else "ANTHROPIC_API_KEY"
        return os.environ.get(env_var, "")

    def has_key(self) -> bool:
        return bool(self.resolved_key())


def config_path() -> Path:
    root = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(root) / "ankify" / "config.json"


def load_config() -> ModelConfig:
    path = config_path()
    if path.exists():
        try:
            return ModelConfig.model_validate_json(path.read_text())
        except (ValueError, OSError):
            pass
    return ModelConfig()


def save_config(config: ModelConfig) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.model_dump_json(indent=2))
    return path
