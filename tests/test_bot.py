"""Tests for src/qayta/bot.py — all Telegram and Gemini calls are mocked."""

from unittest.mock import AsyncMock, MagicMock

import pytest

import qayta.storage as storage_mod
from qayta.bot import (
    classify_and_reply,
    get_user_lang,
    help_handler,
    image_file_handler,
    lang_callback_handler,
    lang_handler,
    other_file_handler,
    photo_handler,
    start_handler,
)
from qayta.vision import ClassificationResult, VisionUnavailable

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_update(user_id: int = 1, message_text: str = "") -> MagicMock:
    """Build a minimal fake Update with a sendable message."""
    update = MagicMock()
    update.effective_user.id = user_id
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()
    update.message.reply_chat_action = AsyncMock()
    return update


def _make_context(vision=None) -> MagicMock:
    """Build a fake Context whose bot_data contains the Vision instance."""
    ctx = MagicMock()
    ctx.bot_data = {"vision": vision or MagicMock()}
    ctx.bot.get_file = AsyncMock()
    return ctx


# ---------------------------------------------------------------------------
# Fixture: isolated in-memory storage for every test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_storage():
    """Re-initialise the storage module with a fresh in-memory DB for each test."""
    # Reset the module-level singleton so each test starts clean.
    storage_mod._conn = None
    storage_mod.init_db(":memory:")
    yield
    # Teardown: close and reset.
    if storage_mod._conn is not None:
        storage_mod._conn.close()
    storage_mod._conn = None


@pytest.fixture(autouse=True)
def fake_settings(monkeypatch, tmp_path):
    """Offline settings (no https webapp_url) and an absent prices file by default."""
    from types import SimpleNamespace

    from qayta import bot as bot_mod
    from qayta import impact

    settings = SimpleNamespace(telegram_bot_token="tok", webapp_url="", admin_user_id=0)
    monkeypatch.setattr(bot_mod, "get_settings", lambda: settings)
    monkeypatch.setattr(impact, "get_settings", lambda: settings)
    monkeypatch.setattr(bot_mod, "_PRICES_PATH", tmp_path / "missing" / "prices.json")
    return settings


# ---------------------------------------------------------------------------
# get_user_lang
# ---------------------------------------------------------------------------


def test_get_user_lang_defaults_to_uz():
    assert get_user_lang(999) == "uz"


def test_get_user_lang_returns_stored_value():
    storage_mod.set_lang(42, "en")
    assert get_user_lang(42) == "en"


# ---------------------------------------------------------------------------
# start_handler / help_handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_handler_replies_in_uz():
    update = _make_update(user_id=1)
    ctx = _make_context()
    await start_handler(update, ctx)
    assert update.message.reply_text.await_count == 2
    text = update.message.reply_text.await_args_list[0].args[0]
    # The Uzbek welcome message contains "Qayta"
    assert "Qayta" in text
    picker = update.message.reply_text.await_args_list[1]
    data = [b.callback_data for b in picker.kwargs["reply_markup"].inline_keyboard[0]]
    assert data == ["lang_uz", "lang_ru", "lang_en"]


@pytest.mark.asyncio
async def test_start_handler_replies_in_stored_lang():
    storage_mod.set_lang(7, "ru")
    update = _make_update(user_id=7)
    update.effective_user.language_code = "en"
    ctx = _make_context()
    await start_handler(update, ctx)
    text = update.message.reply_text.await_args_list[0].args[0]
    assert "Добро пожаловать" in text
    assert storage_mod.get_lang(7) == "ru"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("code", "expected"), [("ru", "ru"), ("en-US", "en"), ("uz", "uz"), ("de", "uz"), (None, "uz")]
)
async def test_start_handler_first_visit_uses_telegram_language(code, expected):
    update = _make_update(user_id=4242)
    update.effective_user.language_code = code
    await start_handler(update, _make_context())
    assert storage_mod.get_lang(4242) == expected


@pytest.mark.asyncio
async def test_help_handler_replies():
    update = _make_update(user_id=1)
    ctx = _make_context()
    await help_handler(update, ctx)
    update.message.reply_text.assert_awaited_once()


# ---------------------------------------------------------------------------
# lang_handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lang_handler_sends_inline_keyboard():
    from telegram import InlineKeyboardMarkup

    update = _make_update(user_id=1)
    ctx = _make_context()
    await lang_handler(update, ctx)
    update.message.reply_text.assert_awaited_once()
    _, kwargs = update.message.reply_text.call_args
    markup = kwargs.get("reply_markup")
    assert isinstance(markup, InlineKeyboardMarkup)
    # Flatten buttons and check callback data
    buttons = [btn for row in markup.inline_keyboard for btn in row]
    cbs = {btn.callback_data for btn in buttons}
    assert cbs == {"lang_uz", "lang_ru", "lang_en"}


# ---------------------------------------------------------------------------
# lang_callback_handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lang_callback_sets_lang_and_confirms():
    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "lang_en"
    update.callback_query.from_user.id = 55
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    ctx = _make_context()
    await lang_callback_handler(update, ctx)

    assert storage_mod.get_lang(55) == "en"
    update.callback_query.answer.assert_awaited_once()
    update.callback_query.edit_message_text.assert_awaited_once()
    confirm_text = update.callback_query.edit_message_text.call_args[0][0]
    # Should contain "English" in the English confirmation string
    assert "English" in confirm_text


@pytest.mark.asyncio
async def test_lang_callback_ru():
    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "lang_ru"
    update.callback_query.from_user.id = 66
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    ctx = _make_context()
    await lang_callback_handler(update, ctx)
    assert storage_mod.get_lang(66) == "ru"


@pytest.mark.asyncio
async def test_lang_callback_ignores_unknown_data():
    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = "lang_xx"
    update.callback_query.from_user.id = 77
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()

    ctx = _make_context()
    await lang_callback_handler(update, ctx)
    update.callback_query.edit_message_text.assert_not_awaited()


# ---------------------------------------------------------------------------
# classify_and_reply
# ---------------------------------------------------------------------------


def _make_vision_result(key: str, confidence: float) -> ClassificationResult:
    from qayta.vision import MaterialKey

    return ClassificationResult(
        material=MaterialKey[key],
        confidence=confidence,
        reason="test",
    )


@pytest.mark.asyncio
async def test_classify_and_reply_unclear_when_decide_returns_none():
    """Low-confidence result → photo.unclear message."""
    vision = AsyncMock()
    # Return a confident-looking result for UNCLEAR key
    vision.classify = AsyncMock(return_value=_make_vision_result("UNCLEAR", 0.9))

    update = _make_update(user_id=1)
    ctx = _make_context(vision=vision)
    await classify_and_reply(update, ctx, b"bytes", "image/jpeg")

    text = update.message.reply_text.call_args[0][0]
    assert "photo" in text.lower() or "rasm" in text.lower() or "фото" in text.lower()


@pytest.mark.asyncio
async def test_classify_and_reply_unclear_when_confidence_below_threshold():
    """Confidence < 0.6 → decide returns None → photo.unclear."""
    vision = AsyncMock()
    vision.classify = AsyncMock(return_value=_make_vision_result("PET_1", 0.5))

    update = _make_update(user_id=1)
    ctx = _make_context(vision=vision)
    await classify_and_reply(update, ctx, b"bytes", "image/jpeg")

    update.message.reply_chat_action.assert_awaited_once()
    text = update.message.reply_text.call_args[0][0]
    # Should be the "unclear" message
    assert "unclear" in text.lower() or "aniq" in text.lower() or "чётко" in text.lower()


@pytest.mark.asyncio
async def test_classify_and_reply_busy_on_vision_unavailable():
    """`VisionUnavailable` → photo.busy message."""
    vision = AsyncMock()
    vision.classify = AsyncMock(side_effect=VisionUnavailable("quota"))

    update = _make_update(user_id=1)
    ctx = _make_context(vision=vision)
    await classify_and_reply(update, ctx, b"bytes", "image/jpeg")

    text = update.message.reply_text.call_args[0][0]
    # Uzbek "band" or Russian "занят" or English "busy"
    assert any(word in text.lower() for word in ("band", "занят", "busy"))


@pytest.mark.asyncio
async def test_classify_and_reply_successful_result():
    """High-confidence PET_1 result → full material reply with tips."""
    vision = AsyncMock()
    vision.classify = AsyncMock(return_value=_make_vision_result("PET_1", 0.9))

    update = _make_update(user_id=1)
    ctx = _make_context(vision=vision)
    await classify_and_reply(update, ctx, b"bytes", "image/jpeg")

    # Check typing action was sent
    update.message.reply_chat_action.assert_awaited_once()
    # Check a reply with parse_mode was sent
    _, kwargs = update.message.reply_text.call_args
    assert kwargs.get("parse_mode") == "Markdown"
    text = update.message.reply_text.call_args[0][0]
    # Must contain the material name and at least one tip bullet
    assert "PET" in text
    assert "•" in text


@pytest.mark.asyncio
async def test_classify_and_reply_recyclable_status():
    """Recyclable material shows recycling indicator."""
    vision = AsyncMock()
    vision.classify = AsyncMock(return_value=_make_vision_result("GLASS", 0.85))

    storage_mod.set_lang(1, "en")
    update = _make_update(user_id=1)
    ctx = _make_context(vision=vision)
    await classify_and_reply(update, ctx, b"bytes", "image/jpeg")

    text = update.message.reply_text.call_args[0][0]
    assert "Recyclable" in text


@pytest.mark.asyncio
async def test_classify_and_reply_not_recyclable_status():
    """Non-recyclable material (TEXTILES) shows the not-recyclable indicator."""
    vision = AsyncMock()
    vision.classify = AsyncMock(return_value=_make_vision_result("TEXTILES", 0.8))

    storage_mod.set_lang(1, "en")
    update = _make_update(user_id=1)
    ctx = _make_context(vision=vision)
    await classify_and_reply(update, ctx, b"bytes", "image/jpeg")

    text = update.message.reply_text.call_args[0][0]
    assert "Not commonly recycled" in text


# ---------------------------------------------------------------------------
# photo_handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_photo_handler_downloads_largest_photo():
    """photo_handler picks the last (largest) PhotoSize and classifies it."""
    vision = AsyncMock()
    vision.classify = AsyncMock(return_value=_make_vision_result("CARDBOARD", 0.9))

    update = _make_update(user_id=1)
    # Simulate two PhotoSize entries; handler should pick the last.
    small = MagicMock()
    small.file_id = "small_id"
    large = MagicMock()
    large.file_id = "large_id"
    update.message.photo = [small, large]

    fake_file = AsyncMock()
    fake_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake_image"))

    ctx = _make_context(vision=vision)
    ctx.bot.get_file = AsyncMock(return_value=fake_file)

    await photo_handler(update, ctx)

    ctx.bot.get_file.assert_awaited_once_with("large_id")
    vision.classify.assert_awaited_once()


# ---------------------------------------------------------------------------
# image_file_handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_image_file_handler_accepts_png():
    """A PNG document within 10 MB goes through classify_and_reply."""
    vision = AsyncMock()
    vision.classify = AsyncMock(return_value=_make_vision_result("PAPER", 0.75))

    update = _make_update(user_id=1)
    doc = MagicMock()
    doc.mime_type = "image/png"
    doc.file_size = 1024 * 100  # 100 KB
    doc.file_id = "png_doc_id"
    update.message.document = doc

    fake_file = AsyncMock()
    fake_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake_png"))

    ctx = _make_context(vision=vision)
    ctx.bot.get_file = AsyncMock(return_value=fake_file)

    await image_file_handler(update, ctx)

    vision.classify.assert_awaited_once()
    _, kwargs = update.message.reply_text.call_args
    assert kwargs.get("parse_mode") == "Markdown"


@pytest.mark.asyncio
async def test_image_file_handler_rejects_pdf():
    """A PDF document gets photo.bad_file — not classified."""
    vision = AsyncMock()
    update = _make_update(user_id=1)
    doc = MagicMock()
    doc.mime_type = "application/pdf"
    doc.file_size = 500_000
    update.message.document = doc

    ctx = _make_context(vision=vision)
    await image_file_handler(update, ctx)

    vision.classify.assert_not_called()
    text = update.message.reply_text.call_args[0][0]
    assert "JPEG" in text or "PNG" in text or "WebP" in text or "image" in text.lower()


@pytest.mark.asyncio
async def test_image_file_handler_rejects_oversized_image():
    """An image file over 10 MB gets photo.bad_file."""
    vision = AsyncMock()
    update = _make_update(user_id=1)
    doc = MagicMock()
    doc.mime_type = "image/jpeg"
    doc.file_size = 11 * 1024 * 1024  # 11 MB
    update.message.document = doc

    ctx = _make_context(vision=vision)
    await image_file_handler(update, ctx)

    vision.classify.assert_not_called()
    update.message.reply_text.assert_awaited_once()


# ---------------------------------------------------------------------------
# other_file_handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_other_file_handler_replies_bad_file():
    update = _make_update(user_id=1)
    ctx = _make_context()
    await other_file_handler(update, ctx)
    update.message.reply_text.assert_awaited_once()
    text = update.message.reply_text.call_args[0][0]
    # Should contain some hint about images
    assert any(word in text for word in ("JPEG", "PNG", "WebP", "rasm", "изображени"))


# ---------------------------------------------------------------------------
# web_app_data_handler
# ---------------------------------------------------------------------------


def _webapp_update(data: str, user_id: int = 5) -> MagicMock:
    update = _make_update(user_id=user_id)
    update.message.web_app_data.data = data
    return update


_POINT = {"type": "point", "name": "Eco", "lat": 41.3, "lon": 69.2, "materials": ["PET_1"]}
_PRICE = {"type": "price", "point_id": "cp-001", "material": "PET_1", "price_som_per_kg": 1200}


@pytest.mark.asyncio
@pytest.mark.parametrize("report", [_POINT, _PRICE])
async def test_web_app_data_valid_report_is_stored(report, monkeypatch):
    import json

    from qayta import bot as bot_mod

    add = MagicMock(return_value=1)
    monkeypatch.setattr(bot_mod.reports, "add_report", add)
    storage_mod.set_lang(5, "en")
    update = _webapp_update(json.dumps(report))

    await bot_mod.web_app_data_handler(update, _make_context())

    add.assert_called_once()
    assert add.call_args.args[0] == report["type"]
    assert add.call_args.args[2] == 5
    update.message.reply_text.assert_awaited_once_with(bot_mod.t("report.received", "en"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        "[]",
        '{"type": "other"}',
        '{"type": "point", "name": "x"}',
        '{"type": "point", "name": "x", "lat": 95, "lon": 0, "materials": ["PET_1"]}',
        '{"type": "point", "name": "x", "lat": "1", "lon": 0, "materials": ["PET_1"]}',
        '{"type": "point", "name": "x", "lat": 1, "lon": 0, "materials": ["NOPE"]}',
        '{"type": "point", "name": "' + "a" * 5000 + '", "lat": 1, "lon": 0, "materials": ["PET_1"]}',
        '{"type": "price", "point_id": "p", "material": "PET_1", "price_som_per_kg": -5}',
        '{"type": "price", "point_id": "p", "material": "PET_1", "price_som_per_kg": true}',
        '{"type": "price", "point_id": "p", "material": "PET_1", "price_som_per_kg": 1e12}',
    ],
)
async def test_web_app_data_invalid_report_is_rejected(raw, monkeypatch):
    from qayta import bot as bot_mod

    add = MagicMock()
    monkeypatch.setattr(bot_mod.reports, "add_report", add)
    update = _webapp_update(raw)

    await bot_mod.web_app_data_handler(update, _make_context())

    add.assert_not_called()
    update.message.reply_text.assert_awaited_once_with(bot_mod.t("report.invalid", "uz"))


# ---------------------------------------------------------------------------
# review_handler
# ---------------------------------------------------------------------------


def _set_admin(monkeypatch, admin_id: int) -> None:
    from qayta import bot as bot_mod

    monkeypatch.setattr(bot_mod, "get_settings", lambda: MagicMock(admin_user_id=admin_id))


@pytest.mark.asyncio
@pytest.mark.parametrize(("admin_id", "user_id"), [(0, 0), (0, 5), (99, 5)])
async def test_review_handler_silent_for_non_admin(monkeypatch, admin_id, user_id):
    from qayta import bot as bot_mod

    _set_admin(monkeypatch, admin_id)
    get_pending = MagicMock(return_value=[])
    monkeypatch.setattr(bot_mod.reports, "get_pending_reports", get_pending)
    update = _make_update(user_id=user_id)

    await bot_mod.review_handler(update, _make_context())

    update.message.reply_text.assert_not_awaited()
    get_pending.assert_not_called()


@pytest.mark.asyncio
async def test_review_handler_empty_queue_replies_none_pending(monkeypatch):
    from qayta import bot as bot_mod

    _set_admin(monkeypatch, 7)
    storage_mod.set_lang(7, "en")
    update = _make_update(user_id=7)

    await bot_mod.review_handler(update, _make_context())

    update.message.reply_text.assert_awaited_once_with(bot_mod.t("review.none_pending", "en"))


@pytest.mark.asyncio
async def test_review_handler_sends_one_message_per_report_with_buttons(monkeypatch):
    from qayta import bot as bot_mod

    _set_admin(monkeypatch, 7)
    first = bot_mod.reports.add_report("point", {"name": "Eco", "materials": ["PET_1", "GLASS"]}, 5)
    second = bot_mod.reports.add_report("price", {"point_id": "cp-001", "price_som_per_kg": 1200}, 6)
    update = _make_update(user_id=7)

    await bot_mod.review_handler(update, _make_context())

    calls = update.message.reply_text.await_args_list
    assert len(calls) == 2
    for call, report_id in zip(calls, (first, second), strict=True):
        buttons = call.kwargs["reply_markup"].inline_keyboard[0]
        assert [b.callback_data for b in buttons] == [
            f"review_approve_{report_id}",
            f"review_reject_{report_id}",
        ]
    assert "point" in calls[0].args[0]
    assert "Eco" in calls[0].args[0]
    assert "PET_1, GLASS" in calls[0].args[0]
    assert "1200" in calls[1].args[0]


def test_review_command_is_registered():
    from telegram.ext import CommandHandler

    from qayta import bot as bot_mod

    app = MagicMock()
    bot_mod.register_handlers(app)

    handlers = [c.args[0] for c in app.add_handler.call_args_list]
    assert any(isinstance(h, CommandHandler) and "review" in h.commands for h in handlers)


# ---------------------------------------------------------------------------
# review_callback_handler
# ---------------------------------------------------------------------------


def _review_update(data: str, user_id: int = 7, text: str = "#1 · point") -> MagicMock:
    update = MagicMock()
    update.callback_query = AsyncMock()
    update.callback_query.data = data
    update.callback_query.from_user.id = user_id
    update.callback_query.message.text = text
    return update


def _stats(user_id: int) -> dict:
    from qayta import impact

    return impact.get_stats(impact.hash_user_id(user_id))


@pytest.fixture
def token(monkeypatch):
    from types import SimpleNamespace

    from qayta import impact

    monkeypatch.setattr(impact, "get_settings", lambda: SimpleNamespace(telegram_bot_token="tok"))


@pytest.mark.asyncio
async def test_review_callback_approve_credits_reporter_once(monkeypatch, token):
    from qayta import bot as bot_mod

    _set_admin(monkeypatch, 7)
    storage_mod.set_lang(7, "en")
    rid = bot_mod.reports.add_report("point", {"name": "Eco"}, 5)
    update = _review_update(f"review_approve_{rid}")

    await bot_mod.review_callback_handler(update, _make_context())

    assert _stats(5)["approved_reports"] == 1
    text = update.callback_query.edit_message_text.await_args.args[0]
    assert bot_mod.t("review.approved", "en") in text
    assert "#1 · point" in text

    await bot_mod.review_callback_handler(_review_update(f"review_approve_{rid}"), _make_context())
    assert _stats(5)["approved_reports"] == 1


@pytest.mark.asyncio
async def test_review_callback_reject_gives_no_points(monkeypatch, token):
    from qayta import bot as bot_mod

    _set_admin(monkeypatch, 7)
    storage_mod.set_lang(7, "en")
    rid = bot_mod.reports.add_report("point", {"name": "Eco"}, 5)
    update = _review_update(f"review_reject_{rid}")

    await bot_mod.review_callback_handler(update, _make_context())

    assert _stats(5)["approved_reports"] == 0
    assert bot_mod.reports.get_pending_reports() == []
    text = update.callback_query.edit_message_text.await_args.args[0]
    assert bot_mod.t("review.rejected", "en") in text


@pytest.mark.asyncio
@pytest.mark.parametrize(("admin_id", "user_id"), [(0, 0), (0, 5), (99, 5)])
async def test_review_callback_ignores_non_admin(monkeypatch, token, admin_id, user_id):
    from qayta import bot as bot_mod

    _set_admin(monkeypatch, admin_id)
    rid = bot_mod.reports.add_report("point", {"name": "Eco"}, 5)
    update = _review_update(f"review_approve_{rid}", user_id=user_id)

    await bot_mod.review_callback_handler(update, _make_context())

    update.callback_query.answer.assert_awaited_once()
    update.callback_query.edit_message_text.assert_not_awaited()
    assert len(bot_mod.reports.get_pending_reports()) == 1


@pytest.mark.asyncio
async def test_review_callback_unknown_report_does_not_crash(monkeypatch, token):
    from qayta import bot as bot_mod

    _set_admin(monkeypatch, 7)
    update = _review_update("review_approve_999")

    await bot_mod.review_callback_handler(update, _make_context())

    update.callback_query.edit_message_text.assert_not_awaited()


def test_review_callback_is_registered():
    from telegram.ext import CallbackQueryHandler

    from qayta import bot as bot_mod

    app = MagicMock()
    bot_mod.register_handlers(app)

    handlers = [c.args[0] for c in app.add_handler.call_args_list]
    matches = [
        h
        for h in handlers
        if isinstance(h, CallbackQueryHandler) and h.pattern and h.pattern.match("review_reject_12")
    ]
    assert len(matches) == 1
    assert not matches[0].pattern.match("review_other_12")


# ---------------------------------------------------------------------------
# stats_handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stats_handler_replies_with_zeros_for_new_user(token):
    from qayta.bot import stats_handler

    storage_mod.set_lang(3, "en")
    update = _make_update(user_id=3)
    await stats_handler(update, _make_context())

    text = update.message.reply_text.call_args.args[0]
    assert "Items sorted: 0" in text
    assert "Points: 0" in text
    assert "Beginner" in text


@pytest.mark.asyncio
async def test_stats_handler_shows_user_counters(token):
    from qayta import impact
    from qayta.bot import stats_handler

    storage_mod.set_lang(4, "en")
    h = impact.hash_user_id(4)
    impact.increment_items(h, 6)
    impact.increment_reports(h, 1)
    update = _make_update(user_id=4)
    await stats_handler(update, _make_context())

    text = update.message.reply_text.call_args.args[0]
    assert "Items sorted: 6" in text
    assert "Approved reports: 1" in text
    assert "Points: 11" in text
    assert "Recycler" in text


@pytest.mark.asyncio
async def test_stats_handler_appends_leaderboard_without_hashes(token):
    from qayta import impact
    from qayta.bot import stats_handler

    storage_mod.set_lang(20, "en")
    h = impact.hash_user_id(20)
    impact.increment_items(h, 3)
    update = _make_update(user_id=20)
    await stats_handler(update, _make_context())

    text = update.message.reply_text.call_args.args[0]
    from qayta.i18n import t

    assert t("stats.leaderboard", "en") in text
    assert f"1. Recycler #{h[:4].upper()} — 3" in text
    assert h not in text


@pytest.mark.asyncio
async def test_stats_handler_me_button_only_for_https(token, fake_settings):
    from qayta import impact
    from qayta.bot import stats_handler

    storage_mod.set_lang(21, "en")
    impact.increment_items(impact.hash_user_id(21), 2)
    update = _make_update(user_id=21)
    await stats_handler(update, _make_context())
    assert update.message.reply_text.call_args.kwargs["reply_markup"] is None

    fake_settings.webapp_url = "https://example.com/app"
    update = _make_update(user_id=21)
    await stats_handler(update, _make_context())
    button = update.message.reply_text.call_args.kwargs["reply_markup"].inline_keyboard[0][0]
    from qayta.i18n import t

    assert button.text == t("stats.open_me_button", "en")
    assert button.web_app.url == "https://example.com/app#me?items=2&reports=0&rank=1"


@pytest.mark.asyncio
async def test_stats_handler_me_url_omits_rank_for_unknown_user(token, fake_settings):
    from qayta.bot import stats_handler

    fake_settings.webapp_url = "https://example.com/app"
    update = _make_update(user_id=22)
    await stats_handler(update, _make_context())
    button = update.message.reply_text.call_args.kwargs["reply_markup"].inline_keyboard[0][0]
    assert button.web_app.url == "https://example.com/app#me?items=0&reports=0"


def test_stats_command_is_registered():
    from telegram.ext import CommandHandler

    from qayta import bot as bot_mod

    app = MagicMock()
    bot_mod.register_handlers(app)

    handlers = [c.args[0] for c in app.add_handler.call_args_list]
    assert any(isinstance(h, CommandHandler) and "stats" in h.commands for h in handlers)


# ---------------------------------------------------------------------------
# report_handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_handler_https_sends_two_webapp_buttons(fake_settings):
    from telegram import ReplyKeyboardMarkup

    from qayta.bot import report_handler
    from qayta.i18n import t

    fake_settings.webapp_url = "https://example.github.io/qayta"
    update = _make_update(user_id=1)
    await report_handler(update, _make_context())

    args, kwargs = update.message.reply_text.call_args
    assert args[0] == t("cmd.report", "uz")
    markup = kwargs["reply_markup"]
    assert isinstance(markup, ReplyKeyboardMarkup)
    assert markup.resize_keyboard and markup.one_time_keyboard
    buttons = [b for row in markup.keyboard for b in row]
    assert [b.web_app.url for b in buttons] == [
        "https://example.github.io/qayta#report?type=point",
        "https://example.github.io/qayta#report?type=price",
    ]
    assert [b.text for b in buttons] == [t("report.point_form", "uz"), t("report.price_form", "uz")]


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["", "http://example.com"])
async def test_report_handler_non_https_replies_text_only(fake_settings, url):
    from qayta.bot import report_handler
    from qayta.i18n import t

    fake_settings.webapp_url = url
    update = _make_update(user_id=1)
    await report_handler(update, _make_context())

    args, kwargs = update.message.reply_text.call_args
    assert args[0] == t("cmd.report", "uz")
    assert kwargs.get("reply_markup") is None


def test_all_six_commands_and_report_are_registered():
    from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

    from qayta import bot as bot_mod

    app = MagicMock()
    bot_mod.register_handlers(app)

    handlers = [c.args[0] for c in app.add_handler.call_args_list]
    commands = {c for h in handlers if isinstance(h, CommandHandler) for c in h.commands}
    assert {"start", "help", "lang", "review", "stats", "report"} <= commands
    callbacks = {h.callback for h in handlers}
    assert {
        bot_mod.report_handler,
        bot_mod.review_callback_handler,
        bot_mod.web_app_data_handler,
        bot_mod.location_handler,
    } <= callbacks
    assert any(isinstance(h, CallbackQueryHandler) for h in handlers)
    assert any(isinstance(h, MessageHandler) for h in handlers)


# ---------------------------------------------------------------------------
# location_handler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_location_handler_stores_location_in_user_data_silently():
    from qayta.bot import location_handler

    update = _make_update(user_id=1)
    update.message.location.latitude = 41.3
    update.message.location.longitude = 69.2
    ctx = _make_context()
    ctx.user_data = {}

    await location_handler(update, ctx)

    assert ctx.user_data["last_location"] == (41.3, 69.2)
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_location_handler_ignores_message_without_location():
    from qayta.bot import location_handler

    update = _make_update(user_id=1)
    update.message.location = None
    ctx = _make_context()
    ctx.user_data = {}

    await location_handler(update, ctx)

    assert ctx.user_data == {}


def test_location_handler_is_registered():
    from telegram.ext import MessageHandler

    from qayta import bot as bot_mod

    app = MagicMock()
    bot_mod.register_handlers(app)

    handlers = [c.args[0] for c in app.add_handler.call_args_list]
    assert any(isinstance(h, MessageHandler) and h.callback is bot_mod.location_handler for h in handlers)


# ---------------------------------------------------------------------------
# classify_and_reply extras: impact, price line, map button, nearest point
# ---------------------------------------------------------------------------


async def _classify(ctx=None, user_id: int = 1, key: str = "PET_1"):
    vision = AsyncMock()
    vision.classify = AsyncMock(return_value=_make_vision_result(key, 0.9))
    update = _make_update(user_id=user_id)
    ctx = ctx or _make_context(vision=vision)
    ctx.bot_data["vision"] = vision
    await classify_and_reply(update, ctx, b"x", "image/jpeg")
    args, kwargs = update.message.reply_text.call_args
    return args[0], kwargs


def _write_prices(monkeypatch, tmp_path, records) -> None:
    import json

    from qayta import bot as bot_mod

    path = tmp_path / "prices.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    monkeypatch.setattr(bot_mod, "_PRICES_PATH", path)


@pytest.mark.asyncio
async def test_classify_increments_impact_counter():
    await _classify(user_id=11)
    assert _stats(11)["items_sorted"] == 1


@pytest.mark.asyncio
async def test_unclear_result_does_not_increment_impact():
    vision = AsyncMock()
    vision.classify = AsyncMock(return_value=_make_vision_result("PET_1", 0.1))
    await classify_and_reply(_make_update(user_id=12), _make_context(vision=vision), b"x", "image/jpeg")
    assert _stats(12)["items_sorted"] == 0


@pytest.mark.asyncio
async def test_no_price_line_when_prices_file_missing_or_invalid(monkeypatch, tmp_path):
    text, _ = await _classify()
    assert "??" not in text
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    from qayta import bot as bot_mod

    monkeypatch.setattr(bot_mod, "_PRICES_PATH", path)
    text, _ = await _classify()
    assert "??" not in text


@pytest.mark.asyncio
async def test_price_line_uses_highest_price_and_flags_outdated(monkeypatch, tmp_path):
    from datetime import UTC, datetime, timedelta

    today = datetime.now(UTC).date().isoformat()
    old = (datetime.now(UTC).date() - timedelta(days=90)).isoformat()
    base = {"point_id": "p", "material": "PET_1", "source": "Phone"}
    _write_prices(
        monkeypatch,
        tmp_path,
        [
            {**base, "price_som_per_kg": 1000, "date": today},
            {**base, "price_som_per_kg": 1500, "date": today},
            {**base, "material": "GLASS", "price_som_per_kg": 9999, "date": today},
        ],
    )
    text, _ = await _classify()
    assert "1500" in text and today in text and "9999" not in text
    assert "eskirgan" not in text

    _write_prices(monkeypatch, tmp_path, [{**base, "price_som_per_kg": 800, "date": old}])
    ctx = _make_context()
    text, _ = await _classify(ctx)
    assert "800" in text and "eskirgan" in text


@pytest.mark.asyncio
async def test_prices_are_cached_in_bot_data(monkeypatch, tmp_path):
    _write_prices(monkeypatch, tmp_path, [])
    ctx = _make_context()
    await _classify(ctx)
    assert ctx.bot_data["prices"] == []


@pytest.mark.asyncio
async def test_map_button_only_for_https_webapp_url(fake_settings):
    _, kwargs = await _classify()
    assert kwargs["reply_markup"] is None

    fake_settings.webapp_url = "http://example.com"
    _, kwargs = await _classify()
    assert kwargs["reply_markup"] is None

    fake_settings.webapp_url = "https://example.com/app"
    _, kwargs = await _classify()
    button = kwargs["reply_markup"].inline_keyboard[0][0]
    assert button.web_app.url == "https://example.com/app#map?material=PET_1"
    assert kwargs["parse_mode"] == "Markdown"


@pytest.mark.asyncio
async def test_nearest_point_appended_when_location_known(monkeypatch):
    from qayta import places

    fetch = AsyncMock(return_value=[{"name": "Eco_Point", "distance_m": 1300.0}])
    monkeypatch.setattr(places, "fetch_nearby", fetch)
    ctx = _make_context()
    ctx.user_data = {"last_location": (41.3, 69.2)}
    text, _ = await _classify(ctx)
    fetch.assert_awaited_once_with(41.3, 69.2, "PET_1")
    assert "EcoPoint" in text and "1.3 km" in text


@pytest.mark.asyncio
async def test_nearest_point_skipped_without_location_or_on_error(monkeypatch):
    from qayta import places

    fetch = AsyncMock(side_effect=RuntimeError("boom"))
    monkeypatch.setattr(places, "fetch_nearby", fetch)
    await _classify()  # MagicMock user_data: no lookup
    fetch.assert_not_awaited()

    ctx = _make_context()
    ctx.user_data = {"last_location": (41.3, 69.2)}
    text, _ = await _classify(ctx)
    assert "??" not in text

    monkeypatch.setattr(places, "fetch_nearby", AsyncMock(return_value=[]))
    text, _ = await _classify(ctx)
    assert "??" not in text


# ---------------------------------------------------------------------------
# Task 7.8 gap fillers: handler-to-service wiring with mocked services
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_app_data_passes_payload_to_add_report(monkeypatch):
    import json

    from qayta import bot as bot_mod

    add = MagicMock(return_value=1)
    monkeypatch.setattr(bot_mod.reports, "add_report", add)

    await bot_mod.web_app_data_handler(_webapp_update(json.dumps(_PRICE), user_id=8), _make_context())

    assert add.call_args.args[1]["price_som_per_kg"] == 1200
    assert add.call_args.args[1]["point_id"] == "cp-001"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "called", "not_called"),
    [("approve", "approve_report", "reject_report"), ("reject", "reject_report", "approve_report")],
)
async def test_review_callback_dispatches_to_matching_service(monkeypatch, action, called, not_called):
    from qayta import bot as bot_mod

    _set_admin(monkeypatch, 7)
    on = MagicMock()
    off = MagicMock()
    monkeypatch.setattr(bot_mod.reports, called, on)
    monkeypatch.setattr(bot_mod.reports, not_called, off)
    update = _review_update(f"review_{action}_42")

    await bot_mod.review_callback_handler(update, _make_context())

    on.assert_called_once_with(42)
    off.assert_not_called()
    update.callback_query.edit_message_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_review_handler_sends_message_for_mocked_pending_report(monkeypatch):
    from qayta import bot as bot_mod

    _set_admin(monkeypatch, 7)
    pending = [{"id": 3, "type": "point", "payload": {"name": "Eco", "materials": ["PET_1"]}}]
    monkeypatch.setattr(bot_mod.reports, "get_pending_reports", MagicMock(return_value=pending))
    update = _make_update(user_id=7)

    await bot_mod.review_handler(update, _make_context())

    update.message.reply_text.assert_awaited_once()
