"""Entry point for the Qayta Telegram bot.

Run with:
    python -m qayta
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

from pydantic import ValidationError
from telegram import BotCommand, MenuButtonWebApp, Update, WebAppInfo
from telegram.error import TelegramError
from telegram.ext import Application, ApplicationBuilder

from qayta import bot, storage
from qayta.config import get_settings
from qayta.vision import Vision

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

# httpx logs every request URL at INFO, and Telegram URLs contain the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[2] / "webapp" / "data"
DATA_FILES = ("points.json", "prices.json")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="qayta", description="Qayta Telegram bot")
    parser.add_argument("--check", action="store_true", help="validate environment and data files, then exit")
    return parser.parse_args(sys.argv[1:] if argv is None else argv)


def _check_data_file(path: Path) -> str | None:
    """Return an error message if *path* is not a readable JSON array, else None."""
    if not path.is_file():
        return f"data file not found: {path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return f"cannot parse {path.name}: {exc}"
    if not isinstance(data, list):
        return f"{path.name} must contain a JSON array"
    return None


def run_check() -> int:
    """Smoke-test settings, DB schema and data files. Return the process exit code."""
    try:
        get_settings()
    except ValidationError as exc:
        names = sorted({str(e["loc"][0]) for e in exc.errors() if e["loc"]})
        print(f"Check failed: invalid or missing settings: {', '.join(names)}")
        return 1
    try:
        storage.init_db(":memory:")
    except Exception as exc:  # noqa: BLE001 - report any schema failure
        print(f"Check failed: database schema creation failed: {exc}")
        return 1
    for name in DATA_FILES:
        error = _check_data_file(DATA_DIR / name)
        if error:
            print(f"Check failed: {error}")
            return 1
    print("Check OK: settings valid, database schema created, data files parsed.")
    return 0


BOT_COMMANDS: dict[str, list[tuple[str, str]]] = {
    "uz": [("start", "Boshlash"), ("lang", "Tilni o'zgartirish"), ("stats", "Mening hissam"),
           ("report", "Punkt yoki narx qo'shish"), ("help", "Yordam")],
    "ru": [("start", "Начать"), ("lang", "Сменить язык"), ("stats", "Мой вклад"),
           ("report", "Добавить пункт или цену"), ("help", "Помощь")],
    "en": [("start", "Start"), ("lang", "Change language"), ("stats", "My impact"),
           ("report", "Add a point or price"), ("help", "Help")],
}


async def set_commands(app: Application) -> None:
    """Publish the command list in uz (default), ru and en; never stop the bot."""
    try:
        for lang, commands in BOT_COMMANDS.items():
            items = [BotCommand(name, description) for name, description in commands]
            if lang == "uz":
                await app.bot.set_my_commands(items)
            await app.bot.set_my_commands(items, language_code=lang)
    except TelegramError as exc:
        logger.warning("Could not set bot commands: %s", type(exc).__name__)


async def post_init(app: Application) -> None:
    """Set commands, and the Mini App menu button when WEBAPP_URL is https; never stop the bot."""
    await set_commands(app)
    webapp_url = get_settings().webapp_url
    if not webapp_url.startswith("https://"):
        return
    try:
        await app.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="🗺 Qayta", web_app=WebAppInfo(url=webapp_url))
        )
    except TelegramError as exc:
        logger.warning("Could not set the Mini App menu button: %s", type(exc).__name__)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.check:
        sys.exit(run_check())

    # ------------------------------------------------------------------
    # 1. Load and validate settings — fail fast with a human-readable msg
    # ------------------------------------------------------------------
    try:
        settings = get_settings()
    except ValidationError as exc:
        missing = [e["loc"][0] for e in exc.errors() if e["type"] == "missing"]
        print(f"Error: missing required environment variables: {', '.join(str(m) for m in missing)}")
        print("Copy .env.example to .env and fill in the values.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 2. Initialise the SQLite database
    # ------------------------------------------------------------------
    storage.init_db(settings.db_path)

    # ------------------------------------------------------------------
    # 3. Build the Telegram Application
    # ------------------------------------------------------------------
    app = ApplicationBuilder().token(settings.telegram_bot_token).post_init(post_init).build()

    # ------------------------------------------------------------------
    # 4. Create the Vision service and attach it to bot_data
    # ------------------------------------------------------------------
    app.bot_data["vision"] = Vision(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
    )

    # ------------------------------------------------------------------
    # 5. Register all Telegram handlers
    # ------------------------------------------------------------------
    bot.register_handlers(app)

    # ------------------------------------------------------------------
    # 6. Start: webhook on a host with a public https URL, otherwise long polling
    # ------------------------------------------------------------------
    logger.info("Qayta bot starting — model=%s db=%s", settings.gemini_model, settings.db_path)
    run(app, settings)


WEBHOOK_PATH = "telegram"


def webhook_secret(token: str) -> str:
    """Derive the Telegram webhook secret from the bot token, so no extra variable is needed."""
    return hashlib.sha256(f"qayta-webhook:{token}".encode()).hexdigest()[:48]


def run(app: Application, settings) -> None:
    """Run in webhook mode when WEBHOOK_URL (or Render's RENDER_EXTERNAL_URL) is https, else long polling."""
    base = (settings.webhook_url or os.environ.get("RENDER_EXTERNAL_URL", "")).rstrip("/")
    if base.startswith("https://"):
        logger.info("Webhook mode on port %d", settings.port)
        app.run_webhook(
            listen="0.0.0.0",
            port=settings.port,
            url_path=WEBHOOK_PATH,
            webhook_url=f"{base}/{WEBHOOK_PATH}",
            secret_token=webhook_secret(settings.telegram_bot_token),
            allowed_updates=Update.ALL_TYPES,
        )
    else:
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
