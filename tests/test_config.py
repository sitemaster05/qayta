"""Tests for qayta.config — settings loading and validation."""


from pathlib import Path

import pydantic
import pytest

import qayta.config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_cache() -> None:
    """Clear the functools.cache on get_settings() between tests."""
    qayta.config.get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Test 1 — importing qayta.config works without any env vars
# ---------------------------------------------------------------------------

def test_import_config_without_env_vars() -> None:
    """Importing qayta.config must not raise even when no env vars are set."""
    # The module is already imported above — just confirm it's accessible.
    assert hasattr(qayta.config, "get_settings")
    assert hasattr(qayta.config, "Settings")


# ---------------------------------------------------------------------------
# Test 2 — missing TELEGRAM_BOT_TOKEN raises ValidationError
# ---------------------------------------------------------------------------

def test_get_settings_raises_when_token_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """get_settings() must raise pydantic.ValidationError when TELEGRAM_BOT_TOKEN is absent."""
    _clear_cache()

    # Change to a temp dir so pydantic-settings won't find a .env file.
    monkeypatch.chdir(tmp_path)

    # Remove the token from the environment (ignore if already absent).
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    # Keep a dummy API key so only the token is missing.
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")

    with pytest.raises(pydantic.ValidationError):
        qayta.config.get_settings()


# ---------------------------------------------------------------------------
# Test 3 — missing GEMINI_API_KEY raises ValidationError
# ---------------------------------------------------------------------------

def test_get_settings_raises_when_gemini_key_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """get_settings() must raise pydantic.ValidationError when GEMINI_API_KEY is absent."""
    _clear_cache()

    monkeypatch.chdir(tmp_path)

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy-token")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(pydantic.ValidationError):
        qayta.config.get_settings()


# ---------------------------------------------------------------------------
# Test 4 — optional fields return correct defaults
# ---------------------------------------------------------------------------

def test_get_settings_optional_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Optional settings fields should carry the documented default values."""
    _clear_cache()

    monkeypatch.chdir(tmp_path)

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy-token")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    # Do NOT set GEMINI_MODEL, WEBAPP_URL, or DB_PATH — let defaults apply.
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("WEBAPP_URL", raising=False)
    monkeypatch.delenv("DB_PATH", raising=False)

    settings = qayta.config.get_settings()

    assert settings.gemini_model == "gemini-flash-lite-latest"
    assert settings.webapp_url == ""
    assert settings.db_path == "data/qayta.db"


# ---------------------------------------------------------------------------
# Test 5 — ADMIN_USER_ID is optional and defaults to 0
# ---------------------------------------------------------------------------

def test_admin_user_id_defaults_to_zero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A missing ADMIN_USER_ID yields 0 (disables /review) and does not raise."""
    _clear_cache()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy-token")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    monkeypatch.delenv("ADMIN_USER_ID", raising=False)

    assert qayta.config.get_settings().admin_user_id == 0


def test_admin_user_id_read_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """ADMIN_USER_ID is parsed as an int when provided."""
    _clear_cache()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy-token")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    monkeypatch.setenv("ADMIN_USER_ID", "123456")

    assert qayta.config.get_settings().admin_user_id == 123456
