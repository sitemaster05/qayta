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
    return SimpleNamespace(bot=SimpleNamespace(set_chat_menu_button=set_button, set_my_commands=AsyncMock()))


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


async def test_post_init_sets_commands_in_three_languages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(entry, "get_settings", lambda: _FakeSettings(""))
    app = _fake_app()
    await entry.post_init(app)  # type: ignore[arg-type]
    codes = {c.kwargs.get("language_code") for c in app.bot.set_my_commands.await_args_list}
    assert codes == {None, "uz", "ru", "en"}
    names = [cmd.command for cmd in app.bot.set_my_commands.await_args_list[0].args[0]]
    assert "lang" in names and "start" in names


class _RunSettings:
    def __init__(self, webhook_url: str, port: int = 10000, token: str = "123:abc") -> None:
        self.webhook_url = webhook_url
        self.port = port
        self.telegram_bot_token = token


def _run_app() -> SimpleNamespace:
    from unittest.mock import MagicMock

    return SimpleNamespace(run_polling=MagicMock())


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Replace serve_webhook with a recorder so run() never opens a socket."""
    calls: dict = {}

    async def fake(app, **kwargs):
        calls.update(kwargs)

    monkeypatch.setattr(entry, "serve_webhook", fake)
    return calls


def test_run_uses_webhook_for_https_url(served: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    app = _run_app()
    entry.run(app, _RunSettings("https://qayta.example.com/"))  # type: ignore[arg-type]
    app.run_polling.assert_not_called()
    assert served["webhook_url"] == "https://qayta.example.com/telegram"
    assert served["port"] == 10000
    assert served["secret"] == entry.webhook_secret("123:abc")
    assert "abc" not in served["secret"]


@pytest.mark.parametrize("url", ["", "http://qayta.example.com"])
def test_run_falls_back_to_polling(url: str, served: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    app = _run_app()
    entry.run(app, _RunSettings(url))  # type: ignore[arg-type]
    assert served == {}
    app.run_polling.assert_called_once()


async def test_web_app_health_and_secret_check() -> None:
    import asyncio

    import tornado.httpclient
    import tornado.httpserver
    import tornado.testing

    queue: asyncio.Queue = asyncio.Queue()
    app = SimpleNamespace(update_queue=queue, bot=None)
    sock, port = tornado.testing.bind_unused_port()
    server = tornado.httpserver.HTTPServer(entry.make_web_app(app, "s3cret"))  # type: ignore[arg-type]
    server.add_sockets([sock])
    client = tornado.httpclient.AsyncHTTPClient()
    base = f"http://127.0.0.1:{port}"
    try:
        ok = await client.fetch(f"{base}/")
        assert ok.code == 200 and ok.body == b"ok"
        bad = await client.fetch(f"{base}/telegram", method="POST", body="{}", raise_error=False)
        assert bad.code == 403 and queue.empty()
        good = await client.fetch(
            f"{base}/telegram",
            method="POST",
            body='{"update_id": 7}',
            headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret"},
            raise_error=False,
        )
        assert good.code == 200
        assert (await queue.get()).update_id == 7
    finally:
        server.stop()


def test_webhook_secret_is_stable_and_valid() -> None:
    import re

    s = entry.webhook_secret("123:abc")
    assert s == entry.webhook_secret("123:abc") and s != entry.webhook_secret("123:abd")
    assert re.fullmatch(r"[A-Za-z0-9_-]{1,256}", s)


def test_run_uses_render_external_url(served: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://qayta-bot.onrender.com")
    app = _run_app()
    entry.run(app, _RunSettings(""))  # type: ignore[arg-type]
    assert served["webhook_url"] == "https://qayta-bot.onrender.com/telegram"
