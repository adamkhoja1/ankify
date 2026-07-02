"""Tests for the global model config (load/save + env fallback)."""

from pathlib import Path

import pytest

from ankify.config import ModelConfig, load_config, save_config


def test_config_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save_config(
        ModelConfig(
            provider="anthropic", model="claude-opus-4-8", reasoning_effort="high", api_key="sk-x"
        )
    )
    loaded = load_config()
    assert loaded.provider == "anthropic" and loaded.model == "claude-opus-4-8"
    assert loaded.api_key == "sk-x" and loaded.has_key()


def test_config_defaults_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = load_config()
    assert cfg.provider == "openai" and cfg.model == "gpt-5.5"
    assert not cfg.has_key()


def test_resolved_key_falls_back_to_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    cfg = ModelConfig(provider="openai", api_key="")
    assert cfg.resolved_key() == "env-key" and cfg.has_key()


def test_saved_config_is_owner_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = save_config(ModelConfig(api_key="sk-secret"))
    assert path.stat().st_mode & 0o777 == 0o600
    # re-saving over a pre-existing (looser) file tightens it too
    path.chmod(0o644)
    save_config(ModelConfig(api_key="sk-secret2"))
    assert path.stat().st_mode & 0o777 == 0o600
