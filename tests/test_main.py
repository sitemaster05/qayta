"""Tests for the --check smoke test in qayta.__main__."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from telegram.error import TelegramError

from qayta import __main__ as entry


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(entry, "DATA_DIR", tmp_path)
    monkeypatch.setattr(entry, "get_settings", lambda: object())
    monkeypatch.setattr(entry.storage, "init_db", lambda *_a, **_k: None)
    for name in entry.DATA_FILES:
        (tmp_path / name).write_text("[]", encoding="utf-8")
    return tmp_path


def test_parse_args_check_flag() -> None:
    assert entry.parse_args(["--check"]).check is True
    assert entry.parse_args([]).check is False


def test_check_success(data_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        entry.main(["--check"])
    assert exc.value.code == 0
    assert "Check OK" in capsys.readouterr().out


def test_check_missing_file(data_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (data_dir / "prices.json").unlink()
    assert entry.run_check() == 1
    assert "not found" in capsys.readouterr().out


def test_check_invalid_json(data_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (data_dir / "points.json").write_text("{oops", encoding="utf-8")
    assert entry.run_check() == 1
    assert "cannot parse" in capsys.readouterr().out


def test_check_not_array(data_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (data_dir / "points.json").write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert entry.run_check() == 1
    assert "JSON array" in capsys.readouterr().out


def test_check_bad_settings(
    data_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom() -> None:
        raise ValidationError.from_exception_data(
            "Settings", [{"type": "missing", "loc": ("TELEGRAM_BOT_TOKEN",), "input": {}}]
        )

    monkeypatch.setattr(entry, "get_settings", boom)
    assert entry.run_check() == 1
    assert "TELEGRAM_BOT_TOKEN" in capsys.readouterr().out


class _FakeSettings:
    def __init__(self, webapp_url: str) -> None:
        self.webapp_url = webapp_url


def _fake_app(error: Exception | None = None) -> SimpleNamespace:
    set_button = AsyncMock(side_effect=error)
    return SimpleNamespace(bot=SimpleNamespace(set_chat_menu_button=set_button))


async def test_post_init_sets_menu_button_for_https(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(entry, "get_settings", lambda: _FakeSettings("https://example.org/app/"))
    app = _fake_app()
    await entry.post_init(app)  # type: ignore[arg-type]
    app.bot.set_chat_menu_button.assert_awaited_once()
    button = app.bot.set_chat_menu_button.await_args.kwargs["menu_button"]
    assert button.web_app.url == "https://example.org/app/"
    assert button.text == "🗺 Qayta"


@pytest.mark.parametrize("url", ["", "http://example.org/"])
async def test_post_init_skips_non_https(monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    monkeypatch.setattr(entry, "get_settings", lambda: _FakeSettings(url))
    app = _fake_app()
    await entry.post_init(app)  # type: ignore[arg-type]
    app.bot.set_chat_menu_button.assert_not_awaited()


async def test_post_init_swallows_telegram_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(entry, "get_settings", lambda: _FakeSettings("https://example.org/"))
    app = _fake_app(TelegramError("boom"))
    await entry.post_init(app)  # type: ignore[arg-type]
    assert "menu button" in caplog.text
