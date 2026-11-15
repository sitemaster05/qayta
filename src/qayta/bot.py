"""Telegram bot handlers for Qayta.

All handlers are async functions with the standard python-telegram-bot signature.
Business logic is delegated to service modules; handlers only do Telegram-specific
work (parse update, send reply).
"""

import json
import logging
import math
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from qayta import impact, places, reports, storage
from qayta.config import get_settings
from qayta.i18n import t
from qayta.materials import CATALOGUE
from qayta.vision import Vision, VisionUnavailable, decide

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language display names (used in confirmation messages)
# ---------------------------------------------------------------------------

_LANG_NAMES: dict[str, str] = {
    "uz": "O'zbek",
    "ru": "Русский",
    "en": "English",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_user_lang(user_id: int) -> str:
    """Return the stored language for *user_id*, defaulting to ``"uz"``."""
    return storage.get_lang(user_id)


def _confidence_band(confidence: float) -> str:
    """Map a confidence float to a loggable band (never logs the raw value)."""
    if confidence >= 0.8:
        return "high"
    if confidence >= 0.6:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to /start with the welcome message in the user's language."""
    user_id = update.effective_user.id  # type: ignore[union-attr]
    lang = get_user_lang(user_id)
    await update.message.reply_text(t("cmd.start", lang))  # type: ignore[union-attr]


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to /help with the usage guide in the user's language."""
    user_id = update.effective_user.id  # type: ignore[union-attr]
    lang = get_user_lang(user_id)
    await update.message.reply_text(t("cmd.help", lang))  # type: ignore[union-attr]


async def lang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to /lang with an inline keyboard for language selection."""
    user_id = update.effective_user.id  # type: ignore[union-attr]
    lang = get_user_lang(user_id)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
                InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
                InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
            ]
        ]
    )
    await update.message.reply_text(t("lang.prompt", lang), reply_markup=keyboard)  # type: ignore[union-attr]


async def lang_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language selection from the inline keyboard."""
    query = update.callback_query
    if query is None:
        return

    await query.answer()

    # Extract the chosen language code from callback_data (e.g. "lang_uz" → "uz").
    data = query.data or ""
    new_lang = data.removeprefix("lang_")
    if new_lang not in _LANG_NAMES:
        return

    user_id = query.from_user.id
    storage.set_lang(user_id, new_lang)

    lang_name = _LANG_NAMES[new_lang]
    await query.edit_message_text(t("lang.changed", new_lang, lang_name=lang_name))


# ---------------------------------------------------------------------------
# Photo classification helpers
# ---------------------------------------------------------------------------


_PRICES_PATH = Path(__file__).resolve().parents[2] / "webapp" / "data" / "prices.json"
_PRICE_STALE_DAYS = 60


def _load_prices(context: ContextTypes.DEFAULT_TYPE) -> list[dict[str, Any]]:
    """Load curated prices once per application; missing or invalid file means no prices."""
    cached = context.bot_data.get("prices")
    if isinstance(cached, list):
        return cached
    try:
        data = json.loads(_PRICES_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = []
    prices = [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []
    context.bot_data["prices"] = prices
    return prices


def _parse_price(record: dict[str, Any], material_key: str) -> tuple[float, str, date] | None:
    """Return ``(price, source, date)`` for a valid record of *material_key*, else ``None``."""
    price = record.get("price_som_per_kg")
    source, raw_date = record.get("source"), record.get("date")
    if record.get("material") != material_key or not _is_number(price) or price <= 0:
        return None
    if not isinstance(source, str) or not source.strip() or not isinstance(raw_date, str):
        return None
    try:
        return price, source, date.fromisoformat(raw_date)
    except ValueError:
        return None


def lookup_price(prices: list[dict[str, Any]], material_key: str) -> dict[str, Any] | None:
    """Return the highest valid price record for *material_key* as a dict, or ``None``."""
    parsed = [p for r in prices if (p := _parse_price(r, material_key))]
    if not parsed:
        return None
    price, source, when = max(parsed, key=lambda p: p[0])
    return {"material": material_key, "price_som_per_kg": price, "source": source, "date": when.isoformat()}


def _price_line(prices: list[dict[str, Any]], material_key: str, lang: str) -> str:
    """Return the localised best-price line for the material, or ``""`` if none is known."""
    best = lookup_price(prices, material_key)
    if best is None:
        return ""
    when = date.fromisoformat(best["date"])
    line = t(
        "price.line", lang, price=f"{best['price_som_per_kg']:g}", source=best["source"], date=best["date"]
    )
    if (datetime.now(UTC).date() - when).days > _PRICE_STALE_DAYS:
        line += f" ({t('price.outdated', lang)})"
    return line


def _map_keyboard(material_key: str, lang: str) -> InlineKeyboardMarkup | None:
    """Mini App button, only when WEBAPP_URL is https (Telegram requires it)."""
    webapp_url = get_settings().webapp_url
    if not webapp_url.startswith("https://"):
        return None
    button = InlineKeyboardButton(
        t("impact.open_map_button", lang),
        web_app=WebAppInfo(url=f"{webapp_url}#map?material={material_key}"),
    )
    return InlineKeyboardMarkup([[button]])


def _format_distance(metres: float) -> str:
    return f"{metres / 1000:.1f} km" if metres >= 1000 else f"{round(metres)} m"


async def _nearest_line(context: ContextTypes.DEFAULT_TYPE, material_key: str, lang: str) -> str:
    """Name of the nearest real point near the user's last shared location, or ``""``."""
    user_data = context.user_data
    location = user_data.get("last_location") if isinstance(user_data, dict) else None
    if not location:
        return ""
    try:
        points = await places.fetch_nearby(location[0], location[1], material_key)
    except Exception:  # noqa: BLE001 - lookup is optional; never log coordinates
        logger.warning("Nearby lookup failed")
        return ""
    if not points:
        return ""
    nearest = points[0]
    name = re.sub(r"[_*`\[\]]", "", nearest.get("name") or "").strip()
    if not name:
        return ""
    return t("nearest.line", lang, name=name, distance=_format_distance(nearest.get("distance_m", 0)))


async def classify_and_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    image_bytes: bytes,
    mime_type: str,
) -> None:
    """Core classification flow shared by photo and image-document handlers.

    1. Sends a typing chat action.
    2. Classifies the image via Gemini.
    3. Replies with the material result, or an appropriate fallback message.

    Args:
        update:      Incoming Telegram update.
        context:     Handler context (``bot_data["vision"]`` must hold the :class:`Vision` instance).
        image_bytes: Raw image bytes in memory — never stored to disk.
        mime_type:   MIME type string, e.g. ``"image/jpeg"``.
    """
    message = update.message  # type: ignore[union-attr]
    user_id = update.effective_user.id  # type: ignore[union-attr]
    lang = get_user_lang(user_id)

    await message.reply_chat_action(ChatAction.TYPING)

    vision_obj: Vision = context.bot_data["vision"]

    try:
        result = await vision_obj.classify(image_bytes, mime_type)
    except VisionUnavailable:
        await message.reply_text(t("photo.busy", lang))
        return

    material = decide(result)

    if material is None:
        await message.reply_text(t("photo.unclear", lang))
        return

    # Log the outcome — never log the exact confidence value.
    confidence_band = _confidence_band(result.confidence if result is not None else 0.0)
    logger.info("Classified: material=%s confidence_band=%s", material.key, confidence_band)

    # Build the localised reply.
    material_name = t(material.name_i18n, lang)
    status_str = t("photo.recyclable" if material.recyclable_uz else "photo.not_recyclable", lang)
    tips_str = "\n".join(f"• {t(tip, lang)}" for tip in material.tips)

    reply_text = t("photo.result", lang, name=material_name, status=status_str, tips=tips_str)

    impact.increment_items(impact.hash_user_id(user_id))

    price_line = _price_line(_load_prices(context), material.key, lang)
    if price_line:
        reply_text += f"\n\n{price_line}"
    nearest_line = await _nearest_line(context, material.key, lang)
    if nearest_line:
        reply_text += f"\n{nearest_line}"

    keyboard = _map_keyboard(material.key, lang)
    await message.reply_text(reply_text, parse_mode="Markdown", reply_markup=keyboard)


# ---------------------------------------------------------------------------
# Message handlers
# ---------------------------------------------------------------------------


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photos sent as Telegram ``PhotoSize`` objects.

    Downloads the largest available resolution into memory and classifies it.
    """
    message = update.message  # type: ignore[union-attr]
    if not message or not message.photo:
        return

    # The last element is always the highest resolution.
    photo = message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytearray = bytearray()
    await file.download_as_bytearray(image_bytearray)  # type: ignore[arg-type]

    await classify_and_reply(update, context, bytes(image_bytearray), "image/jpeg")


async def image_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle image files sent as documents (JPEG, PNG, WebP up to 10 MB).

    Other formats or oversized files are redirected to ``other_file_handler``.
    """
    message = update.message  # type: ignore[union-attr]
    if not message or not message.document:
        return

    document = message.document
    allowed_mimes = {"image/jpeg", "image/png", "image/webp"}
    max_size = 10 * 1024 * 1024  # 10 MB

    user_id = update.effective_user.id  # type: ignore[union-attr]
    lang = get_user_lang(user_id)

    if document.mime_type not in allowed_mimes or (document.file_size or 0) > max_size:
        await message.reply_text(t("photo.bad_file", lang))
        return

    file = await context.bot.get_file(document.file_id)
    image_bytearray = bytearray()
    await file.download_as_bytearray(image_bytearray)  # type: ignore[arg-type]

    await classify_and_reply(update, context, bytes(image_bytearray), document.mime_type)


async def other_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch-all handler for documents that are not supported images."""
    message = update.message  # type: ignore[union-attr]
    if not message:
        return
    user_id = update.effective_user.id  # type: ignore[union-attr]
    lang = get_user_lang(user_id)
    await message.reply_text(t("photo.bad_file", lang))


# ---------------------------------------------------------------------------
# Mini App report handling
# ---------------------------------------------------------------------------

_MAX_WEBAPP_DATA_CHARS = 4096  # Telegram allows up to 4096 bytes; reject anything bigger.
_MAX_NAME = 100
_MAX_PHONE = 30
_MAX_HOURS = 100
_MAX_POINT_ID = 64
_MAX_MATERIALS = len(CATALOGUE)
_MAX_PRICE_SOM_PER_KG = 10_000_000


def _is_number(value: Any) -> bool:
    """True for finite int/float values (bool is not a number here)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value)


def _clean_str(value: Any, max_len: int, *, required: bool) -> str | None:
    """Return the stripped string, ``""`` for an absent optional value, or ``None`` if invalid."""
    if value is None and not required:
        return ""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if len(value) > max_len or (required and not value):
        return None
    return value


def _validate_point(data: dict[str, Any]) -> dict[str, Any] | None:
    name = _clean_str(data.get("name"), _MAX_NAME, required=True)
    phone = _clean_str(data.get("phone"), _MAX_PHONE, required=False)
    hours = _clean_str(data.get("hours"), _MAX_HOURS, required=False)
    lat, lon = data.get("lat"), data.get("lon")
    materials = data.get("materials")
    if name is None or phone is None or hours is None:
        return None
    if not (_is_number(lat) and _is_number(lon)) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    if not isinstance(materials, list) or not 1 <= len(materials) <= _MAX_MATERIALS:
        return None
    if not all(isinstance(m, str) and m in CATALOGUE for m in materials):
        return None
    payload: dict[str, Any] = {
        "name": name,
        "lat": lat,
        "lon": lon,
        "materials": list(dict.fromkeys(materials)),
    }
    if phone:
        payload["phone"] = phone
    if hours:
        payload["hours"] = hours
    return payload


def _validate_price(data: dict[str, Any]) -> dict[str, Any] | None:
    point_id = _clean_str(data.get("point_id"), _MAX_POINT_ID, required=True)
    material = data.get("material")
    price = data.get("price_som_per_kg")
    if point_id is None or not isinstance(material, str) or material not in CATALOGUE:
        return None
    if not _is_number(price) or not 0 < price <= _MAX_PRICE_SOM_PER_KG:
        return None
    return {"point_id": point_id, "material": material, "price_som_per_kg": price}


def parse_report(raw: Any) -> tuple[str, dict[str, Any]] | None:
    """Validate raw ``web_app_data`` text; return ``(type, clean_payload)`` or ``None``."""
    if not isinstance(raw, str) or len(raw) > _MAX_WEBAPP_DATA_CHARS:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    validators = {"point": _validate_point, "price": _validate_price}
    kind = data.get("type")
    validator = validators.get(kind) if isinstance(kind, str) else None
    if validator is None:
        return None
    payload = validator(data)
    return None if payload is None else (kind, payload)


async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Store a community report sent from the Mini App via ``sendData``."""
    message = update.message  # type: ignore[union-attr]
    if not message or not message.web_app_data:
        return
    user_id = update.effective_user.id  # type: ignore[union-attr]
    lang = get_user_lang(user_id)

    parsed = parse_report(message.web_app_data.data)
    if parsed is None:
        # Never log the payload: it may contain a location.
        logger.info("Rejected invalid Mini App report")
        await message.reply_text(t("report.invalid", lang))
        return

    kind, payload = parsed
    reports.add_report(kind, payload, user_id)
    logger.info("Stored Mini App report: type=%s", kind)
    await message.reply_text(t("report.received", lang))


def _report_keyboard(lang: str) -> ReplyKeyboardMarkup | None:
    """Reply keyboard with Mini App report forms; ``sendData`` needs a reply-keyboard WebApp button."""
    webapp_url = get_settings().webapp_url
    if not webapp_url.startswith("https://"):
        return None
    buttons = [
        KeyboardButton(
            t(label_key, lang),
            web_app=WebAppInfo(url=f"{webapp_url}#report?type={kind}"),
        )
        for label_key, kind in (("report.point_form", "point"), ("report.price_form", "price"))
    ]
    return ReplyKeyboardMarkup([buttons], resize_keyboard=True, one_time_keyboard=True)


async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to /report with the Mini App report forms (buttons only when WEBAPP_URL is https)."""
    message = update.message  # type: ignore[union-attr]
    if message is None:
        return
    user_id = update.effective_user.id  # type: ignore[union-attr]
    lang = get_user_lang(user_id)
    await message.reply_text(t("cmd.report", lang), reply_markup=_report_keyboard(lang))


async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remember the shared location in memory only (never stored in the DB, never logged)."""
    message = update.message  # type: ignore[union-attr]
    if not message or not message.location:
        return
    context.user_data["last_location"] = (  # type: ignore[index]
        message.location.latitude,
        message.location.longitude,
    )


def _report_summary(report: dict[str, Any]) -> str:
    """Compact human-readable summary of a pending report (type and payload fields)."""
    lines = [f"#{report['id']} · {report['type']}"]
    for key, value in report["payload"].items():
        text = ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)
        lines.append(f"{key}: {text}")
    return "\n".join(lines)


async def review_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send each pending report to the admin with Approve/Reject buttons (admin only)."""
    message = update.message  # type: ignore[union-attr]
    user_id = update.effective_user.id  # type: ignore[union-attr]
    admin_id = get_settings().admin_user_id
    if admin_id == 0 or user_id != admin_id or message is None:
        return

    lang = get_user_lang(user_id)
    pending = reports.get_pending_reports()
    if not pending:
        await message.reply_text(t("review.none_pending", lang))
        return

    for report in pending:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Approve ✅", callback_data=f"review_approve_{report['id']}"),
                    InlineKeyboardButton("Reject ❌", callback_data=f"review_reject_{report['id']}"),
                ]
            ]
        )
        await message.reply_text(_report_summary(report), reply_markup=keyboard)


async def review_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Approve or reject a report from the admin's inline buttons (admin only).

    ``reports.approve_report`` already credits the reporter, so no points are added here.
    """
    query = update.callback_query
    if query is None:
        return
    await query.answer()

    admin_id = get_settings().admin_user_id
    if admin_id == 0 or query.from_user.id != admin_id:
        return

    _, action, raw_id = (query.data or "").split("_", 2)
    report_id = int(raw_id)
    lang = get_user_lang(admin_id)

    try:
        if action == "approve":
            reports.approve_report(report_id)
        else:
            reports.reject_report(report_id)
    except KeyError:
        logger.info("Review of unknown report ignored")
        return

    status = t("review.approved" if action == "approve" else "review.rejected", lang)
    summary = query.message.text if query.message and isinstance(query.message.text, str) else ""
    await query.edit_message_text(f"{summary}\n\n{status}" if summary else status)


async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply to /stats with the user's impact counters, points and level."""
    message = update.message  # type: ignore[union-attr]
    if message is None:
        return
    user_id = update.effective_user.id  # type: ignore[union-attr]
    lang = get_user_lang(user_id)
    user_hash = impact.hash_user_id(user_id)
    stats = impact.get_stats(user_hash)
    text = t(
        "stats.result",
        lang,
        items=stats["items_sorted"],
        reports=stats["approved_reports"],
        points=stats["points"],
        level=t(stats["level"], lang),
    )
    board = impact.get_leaderboard(10)
    if board:
        lines = [f"{i}. {e['alias']} — {e['points']}" for i, e in enumerate(board, start=1)]
        text = f"{text}\n\n{t('stats.leaderboard', lang)}\n" + "\n".join(lines)
    await message.reply_text(text, reply_markup=_me_keyboard(stats, impact.get_rank(user_hash), lang))


def _me_keyboard(stats: dict, rank: int | None, lang: str) -> InlineKeyboardMarkup | None:
    """Mini App 'Me' tab button, only when WEBAPP_URL is https (Telegram requires it)."""
    webapp_url = get_settings().webapp_url
    if not webapp_url.startswith("https://"):
        return None
    url = f"{webapp_url}#me?items={stats['items_sorted']}&reports={stats['approved_reports']}"
    if rank is not None:
        url += f"&rank={rank}"
    button = InlineKeyboardButton(t("stats.open_me_button", lang), web_app=WebAppInfo(url=url))
    return InlineKeyboardMarkup([[button]])


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------


def register_handlers(app: Application) -> None:  # type: ignore[type-arg]
    """Register all handlers with *app* in priority order.

    Args:
        app: The :class:`~telegram.ext.Application` instance built in ``__main__``.
    """
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("lang", lang_handler))
    app.add_handler(CommandHandler("review", review_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CommandHandler("report", report_handler))
    app.add_handler(CallbackQueryHandler(lang_callback_handler, pattern=r"^lang_(uz|ru|en)$"))
    app.add_handler(CallbackQueryHandler(review_callback_handler, pattern=r"^review_(approve|reject)_\d+$"))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.Document.IMAGE, image_file_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, other_file_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
