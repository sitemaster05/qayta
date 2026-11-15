# Requirements — core-bot

## Introduction

Qayta is a Telegram bot that helps residents of Uzbekistan identify recyclable materials from a photo and
learn how to prepare them. This spec covers the foundational layer of the project: project skeleton,
configuration, internationalisation, the `/start`, `/help`, and `/lang` commands, the material catalogue,
and the photo-classification flow powered by Google Gemini.

Collection points and the Mini App map are **out of scope** for this spec; they are covered by separate
specs (`nearby-points` and `map-mini-app`).

---

## Requirements

### 1 — Project skeleton

**Requirement 1.1**
The repository MUST follow the `src/` layout with package `qayta` under `src/qayta/`.

**Requirement 1.2**
`pyproject.toml` MUST declare the project metadata, all runtime dependencies (pinned to compatible
versions), and dev/test dependency groups. The entry point `python -m qayta` MUST start the bot.

**Requirement 1.3**
The module layout inside `src/qayta/` MUST match the structure defined in the steering docs:
`__main__.py`, `config.py`, `bot.py`, `vision.py`, `materials.py`, `i18n.py`, and `storage.py`.
Modules not yet needed by this spec (`places.py`, `impact.py`) MAY be created as stubs.

**Requirement 1.4**
A `tests/` directory MUST be present and runnable with `pytest`. Tests MUST run fully offline (no live
Telegram, Gemini, or Overpass calls).

---

### 2 — Configuration

**Requirement 2.1**
All sensitive configuration MUST be read from environment variables. The variables are:
`TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, `GEMINI_MODEL` (default `gemini-2.5-flash`), `WEBAPP_URL`
(optional, may be empty).

**Requirement 2.2**
`config.py` MUST use `pydantic-settings` to parse and validate these variables. Importing any module MUST
NOT require the variables (tests run without a `.env`). Validation happens when `get_settings()` is first
called from `main()`; the app MUST then exit with a clear error message if `TELEGRAM_BOT_TOKEN` or
`GEMINI_API_KEY` is missing.

**Requirement 2.4**
The SQLite database MUST default to `data/qayta.db` (the `data/` folder is git-ignored) and the folder MUST
be created if it does not exist.

**Requirement 2.3**
`.env.example` MUST list all variable names with empty values and a short comment. Secrets MUST NOT be
committed.

---

### 3 — Internationalisation (i18n)

**Requirement 3.1**
All user-facing text MUST live in `locales/uz.json`, `locales/ru.json`, and `locales/en.json`. No
user-visible string may be hard-coded in a handler or service module.

**Requirement 3.2**
All three locale files MUST have **identical key sets**. Any key or `{placeholder}` present in one file
MUST be present in all others. Keys use one dotted style everywhere: `cmd.start`, `cmd.help`,
`lang.prompt`, `lang.changed`, `photo.unclear`, `photo.busy`, `photo.bad_file`, `photo.result`,
`photo.recyclable`, `photo.not_recyclable`, `mat.<KEY>`, `tip.<name>`.

**Requirement 3.3**
`i18n.py` MUST expose a `t(key: str, lang: str, **kwargs) -> str` function that returns the formatted
string for the given key and language, falling back to `"en"` if the requested language is unavailable.

**Requirement 3.4**
A property-based test (Hypothesis) MUST verify that every key in every locale file can be formatted with
the same placeholder names without raising an exception.

---

### 4 — `/lang` command

**Requirement 4.1**
The bot MUST handle the `/lang` command and reply with an inline keyboard offering `🇺🇿 Uzbek`,
`🇷🇺 Русский`, and `🇬🇧 English`.

**Requirement 4.2**
When the user taps a language button, the bot MUST store the selection per `user_id` in SQLite and
confirm the change in the newly selected language.

**Requirement 4.3**
The stored language preference MUST be used for all subsequent messages to that user. Users who have
never set a language default to `"uz"`.

---

### 5 — `/start` and `/help` commands

**Requirement 5.1**
`/start` MUST send a welcome message in the user's language (from i18n) that briefly explains what the
bot does and invites the user to send a photo.

**Requirement 5.2**
`/help` MUST send a short usage guide in the user's language listing the available commands and what the
bot can and cannot do (no collection points or map in this spec).

---

### 6 — Material catalogue

**Requirement 6.1**
`materials.py` MUST define a catalogue of at least the following material types:
`PET_1`, `HDPE_2`, `PP_5`, `GLASS`, `PAPER`, `CARDBOARD`, `ALUMINIUM`, `STEEL`, `BATTERIES`,
`EWASTE`, `TEXTILES`, `ORGANIC`, `MIXED`.

**Requirement 6.2**
Each entry MUST contain:
- a canonical i18n key used to look up the localised material name,
- a boolean flag `recyclable_uz` meaning "commonly accepted by collection points in Uzbekistan" (general
  guidance, not a legal rule — the README says so),
- a list of 1–3 preparation-tip i18n keys,
- an OSM `recycling:*` tag key (for future use by `nearby-points`),
- an average item weight in grams (for future use by `impact`).

**Requirement 6.3**
A property-based test MUST verify that every material entry has a non-empty tips list, that each tip key
resolves to a non-empty string in all three locales, and that the material name key resolves in all three
locales.

---

### 7 — Photo classification flow

**Requirement 7.1**
When a user sends a photo, the bot MUST forward the highest-resolution version to `vision.py` for
classification. Images sent as a file (document with MIME type `image/jpeg`, `image/png` or `image/webp`,
up to 10 MB) MUST be handled the same way; other documents get a short localised hint (`photo.bad_file`).

**Requirement 7.2**
`vision.py` MUST create one Gemini client at startup and call the **async** API
(`client.aio.models.generate_content`) so the event loop is never blocked. It MUST request real structured
output: `response_mime_type="application/json"` plus `response_schema`, where `material` is an enum of the
catalogue keys plus `UNCLEAR` (for photos that are not a single waste item, e.g. people, screenshots,
several items). The expected schema is:

```json
{
  "material": "<one of the catalogue keys or UNCLEAR>",
  "confidence": 0.0,
  "reason": "<one short sentence>"
}
```

The response MUST be validated with a Pydantic v2 model. If validation fails, treat the result as unclear.

**Requirement 7.2a**
The decision logic MUST live in one pure function `vision.decide(result) -> Material | None`, returning
`None` when the result is missing, the material is `UNCLEAR` or not in the catalogue, or
`confidence < 0.6`. Handlers only call this function. Unit and property-based (Hypothesis) tests MUST
cover it, including the 0.6 boundary.

**Requirement 7.3**
If `decide` returns a material, the bot MUST reply with:
1. The localised material name.
2. A localised recyclability status for Uzbekistan (e.g. "♻️ Recyclable in Uzbekistan" or
   "🚫 Not commonly recycled in Uzbekistan").
3. The 1–3 localised preparation tips as a short list.

**Requirement 7.4**
If `decide` returns `None`, the bot MUST reply with a polite, localised message asking the user to send a
clearer photo (`photo.unclear`). The bot MUST NOT guess or fabricate a classification in this case.

**Requirement 7.4a**
Gemini quota errors (HTTP 429), timeouts and network errors MUST produce a separate localised message
(`photo.busy`: "the service is busy, please try again in a minute"), not the "clearer photo" message.

**Requirement 7.5**
Photos MUST be processed in memory and MUST NOT be stored to disk or any database.

**Requirement 7.6**
While the classification is in progress the bot MUST send a "typing…" chat action so the user sees
feedback.

---

### 8 — Logging and privacy

**Requirement 8.1**
The bot MUST log classification outcomes (material key and confidence band) using Python's `logging`
module.

**Requirement 8.2**
The bot MUST NOT log the photo content, the Gemini API key, the Telegram token, or exact user IDs in
any message more verbose than `DEBUG`.
