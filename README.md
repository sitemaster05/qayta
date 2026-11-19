# Qayta — Recycle smarter in Uzbekistan

*Qayta* means "again / once more" in Uzbek. Qayta is a Telegram bot (and a Telegram Mini App map) that
helps residents of Uzbekistan and Central Asia answer two questions before throwing something away:

1. **Can this be recycled, and how do I prepare it?** — send a photo, get an instant answer.
2. **Where can I hand it in?** — share your location and see the nearest collection points from
   OpenStreetMap.
3. **What do buyers pay?** — real per-kg prices from public buy ads, each with its source and date.

**Try it:** bot [@AICiroPRobot](https://t.me/AICiroPRobot) · Mini App <https://sitemaster05.github.io/qayta/> · Demo video <https://youtu.be/yI6kezZ6bk8>
(opens best inside Telegram) · Languages: O'zbek, Русский, English.

**Built with Kiro for Kiroween 2026.** Specs, steering and task history are in [`.kiro/`](.kiro/). How we used
Kiro, what worked and what we fixed by hand: [`docs/KIRO_WRITEUP.md`](docs/KIRO_WRITEUP.md).

---

## Quick start

```bash
cp .env.example .env          # fill in TELEGRAM_BOT_TOKEN and GEMINI_API_KEY
pip install -e ".[dev]"
python -m qayta
```

---

## Configuration

See `.env.example` for all environment variables.

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Bot token from @BotFather |
| `GEMINI_API_KEY` | ✅ | — | Google AI Studio API key |
| `GEMINI_MODEL` | | `gemini-flash-lite-latest` | Gemini model name |
| `WEBAPP_URL` | | *(empty)* | GitHub Pages URL for the Mini App map |
| `DB_PATH` | | `data/qayta.db` | SQLite database path |

---

## Recyclability in Uzbekistan (`recyclable_uz`)

Each material entry in `src/qayta/materials.py` carries a `recyclable_uz` boolean flag.
**This is general guidance only, based on what collection points in Tashkent, Samarkand, and
Ohangaron commonly accept. It is not a legal or regulatory classification.**
Availability varies by city, district, and operator — always confirm with your local recycling
point before making a trip.

---

## Hosting (free, 24/7)

The bot runs in **webhook mode** when it has a public https URL, and in long-polling mode otherwise.

1. On [Render](https://render.com) choose *New → Blueprint* and pick this repository; `render.yaml` creates a free
   web service `qayta-bot` (`pip install .`, `python -m qayta`).
2. Enter `TELEGRAM_BOT_TOKEN` and `GEMINI_API_KEY` (and optionally `ADMIN_USER_ID`) when Render asks.
3. Render sets `PORT` and `RENDER_EXTERNAL_URL`; the bot registers its webhook at `<url>/telegram` with a secret
   token derived from the bot token. Stop any locally running copy, because Telegram allows either a webhook
   or polling, not both.
4. Free Render services sleep after 15 idle minutes. The `keep-alive` GitHub Action pings the service every
   10 minutes once the repository variable `QAYTA_BOT_URL` is set to the Render URL.

The free filesystem is ephemeral: SQLite stats reset when Render restarts the service.

---

## Running tests

```bash
pytest
ruff check src/ tests/
```

Tests run fully offline; all external services (Telegram, Gemini, Overpass) are mocked.

---

## Project structure

```
src/qayta/       — bot package
locales/         — uz.json, ru.json, en.json (all user-facing text)
webapp/          — Telegram Mini App map (static, GitHub Pages)
tests/           — mirrors src/qayta/ module names
```

---

## Attribution

Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright).
