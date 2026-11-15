# Design — core-bot

## Overview

This document describes the architecture and module-level design for the `core-bot` spec. The goal is a
thin, testable Python package that wires together `python-telegram-bot`, Google Gemini, and a small SQLite
database — without any code for collection points or the Mini App (those are separate specs).

---

## Directory layout

```
qayta/
├── pyproject.toml
├── .env.example
├── locales/
│   ├── uz.json
│   ├── ru.json
│   └── en.json
├── src/
│   └── qayta/
│       ├── __init__.py
│       ├── __main__.py
│       ├── config.py
│       ├── bot.py
│       ├── vision.py
│       ├── materials.py
│       ├── i18n.py
│       └── storage.py
└── tests/
    ├── conftest.py
    ├── test_materials.py
    ├── test_i18n.py
    ├── test_vision.py
    └── test_bot.py
```

---

## Module designs

### `config.py`

Uses `pydantic-settings` `BaseSettings` to parse environment variables.

```python
class Settings(BaseSettings):
    telegram_bot_token: str
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    webapp_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

A module-level `get_settings()` function (wrapped in `functools.cache`) returns a cached singleton. Nothing
is validated at import time, so tests can import every module without a `.env`. `main()` calls
`get_settings()` first; on `ValidationError` it logs which variables are missing and exits with code 1.
An extra optional field `db_path: str = "data/qayta.db"` is read from `DB_PATH`.

---

### `materials.py`

Defines two types and a catalogue dict.

**`Material` dataclass**

```python
@dataclass(frozen=True)
class Material:
    key: str                # e.g. "PET_1"
    name_i18n: str          # i18n key for the localised name
    recyclable_uz: bool
    tips: list[str]         # 1–3 i18n keys for preparation tips
    osm_tag: str            # e.g. "recycling:plastic_bottles"
    avg_weight_g: float     # average item weight in grams
```

**`CATALOGUE: dict[str, Material]`** — keyed by the material identifier string (e.g. `"PET_1"`). This is
the single source of truth; every other module imports from here.

Material identifiers: `PET_1`, `HDPE_2`, `PP_5`, `GLASS`, `PAPER`, `CARDBOARD`, `ALUMINIUM`, `STEEL`,
`BATTERIES`, `EWASTE`, `TEXTILES`, `ORGANIC`, `MIXED`.

---

### `i18n.py`

Loads all three locale files at module import time into a dict `_STRINGS: dict[str, dict[str, str]]`
(outer key = language code, inner key = translation key).

```python
def t(key: str, lang: str, **kwargs: object) -> str:
    strings = _STRINGS.get(lang) or _STRINGS["en"]
    template = strings.get(key, key)   # fall back to the key itself so nothing crashes
    return template.format(**kwargs)
```

Locale files use standard Python `str.format` placeholders: `{name}`, `{tips}`, etc.

---

### `storage.py`

A thin wrapper around `sqlite3`. Creates the DB file at `settings.db_path` (default `data/qayta.db`,
git-ignored) and creates the parent folder if it is missing. Tests use `":memory:"`.

Tables in scope for this spec:

```sql
CREATE TABLE IF NOT EXISTS user_language (
    user_id   INTEGER PRIMARY KEY,
    lang      TEXT    NOT NULL DEFAULT 'uz'
);
```

Exposed helpers:
- `get_lang(user_id: int) -> str` — returns `"uz"` if no row found.
- `set_lang(user_id: int, lang: str) -> None`

The module is synchronous (SQLite is synchronous); handlers call it from a `run_in_executor` wrapper or
directly since the operations are fast.

---

### `vision.py`

#### Pydantic schema

```python
MaterialKey = Enum("MaterialKey", {k: k for k in [*CATALOGUE, "UNCLEAR"]}, type=str)

class ClassificationResult(BaseModel):
    material: MaterialKey
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(max_length=200)

class VisionUnavailable(Exception):
    """Gemini quota (429), timeout or network failure — the bot answers `photo.busy`."""
```

#### `class Vision` — created once in `main()` and stored in `application.bot_data`

- `__init__(settings)` builds a single `google.genai.Client(api_key=...)`.
- `async def classify(image_bytes: bytes, mime_type: str) -> ClassificationResult | None`
  1. Calls `await client.aio.models.generate_content(...)` with the image part and `CLASSIFICATION_PROMPT`.
  2. Generation config: `response_mime_type="application/json"`, `response_schema=ClassificationResult`,
     `temperature=0`; the whole call is wrapped in `asyncio.timeout(30)`.
  3. Quota/HTTP 429, timeout and network errors raise `VisionUnavailable`.
  4. Malformed JSON or schema mismatch returns `None` (treated as unclear).

#### `def decide(result: ClassificationResult | None) -> Material | None`

Pure function, the single place for the decision rule: returns `None` if `result is None`, the material is
`UNCLEAR` or not in `CATALOGUE`, or `confidence < CONFIDENCE_THRESHOLD` (0.6); otherwise the catalogue
entry.

The system prompt is stored as a module-level constant `CLASSIFICATION_PROMPT` so it can be inspected
and tested without triggering a network call. It tells the model to answer `UNCLEAR` for people,
screenshots, documents or photos with several different items.

---

### `bot.py`

Sets up `python-telegram-bot` handlers. All handlers are `async` functions. Business logic is delegated
to service modules; handlers contain only Telegram-specific code (parse update, send reply).

| Handler | Trigger | Action |
|---|---|---|
| `start_handler` | `/start` | Reply with `t("start_message", lang)` |
| `help_handler` | `/help` | Reply with `t("help_message", lang)` |
| `lang_handler` | `/lang` | Reply with inline keyboard (3 buttons) |
| `lang_callback_handler` | `CallbackQuery` matching `"lang_"` prefix | Store lang, confirm |
| `photo_handler` | `MessageHandler(filters.PHOTO)` | Run photo flow |
| `image_file_handler` | `MessageHandler(filters.Document.IMAGE)` | Same flow for jpeg/png/webp ≤ 10 MB |
| `other_file_handler` | `MessageHandler(filters.Document.ALL)` | Reply `photo.bad_file` |

**Photo flow (shared helper `classify_and_reply`):**
1. Send `ChatAction.TYPING`.
2. Download the bytes into memory (`bytearray`), never to disk.
3. `result = await vision.classify(image_bytes, mime_type)`; on `VisionUnavailable` reply `photo.busy`.
4. `material = vision.decide(result)`; if `None`, reply `photo.unclear`.
5. Otherwise build the reply from `mat.<KEY>`, `photo.recyclable` / `photo.not_recyclable` and the tips,
   formatted with `photo.result`.

Helper `get_user_lang(user_id: int) -> str` wraps `storage.get_lang` and is shared between handlers.

---

### `__main__.py`

```python
def main() -> None:
    settings = get_settings()
    app = ApplicationBuilder().token(settings.telegram_bot_token).build()
    # register handlers from bot.py
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
```

---

## Locale file structure

Each locale file is a flat JSON object. Keys follow the dotted pattern `area.purpose`:

```jsonc
{
  // Commands
  "cmd.start": "...",
  "cmd.help": "...",

  // Language selection
  "lang.prompt": "...",
  "lang.changed": "...",

  // Photo flow
  "photo.unclear": "...",
  "photo.busy": "...",
  "photo.bad_file": "...",
  "photo.recyclable": "♻️ ...",
  "photo.not_recyclable": "🚫 ...",
  "photo.result": "...",      // uses {name}, {status}, {tips}

  // Material names  (one key per material)
  "mat.PET_1": "PET Plastic #1",
  "mat.HDPE_2": "...",
  // ... all 13 materials

  // Preparation tips  (shared across materials where applicable)
  "tip.rinse": "...",
  "tip.remove_cap": "...",
  "tip.flatten": "...",
  "tip.dry": "...",
  "tip.separate_pages": "...",
  "tip.remove_staples": "...",
  "tip.discharge": "...",
  "tip.handle_safely": "...",
  "tip.remove_batteries": "...",
  "tip.keep_whole": "...",
  "tip.bag_separately": "...",
  "tip.no_preparation": "..."
}
```

---

## Test design

### `tests/test_i18n.py`

- **Unit:** `t()` with a known key returns the right string.
- **Unit:** `t()` with an unknown language falls back to English.
- **Property (Hypothesis):** For every locale and every key, calling `t(key, lang)` with the correct
  placeholders does not raise. Strategy: enumerate keys from `uz.json`, derive expected placeholders via
  regex, supply dummy string values.

### `tests/test_materials.py`

- **Unit:** `CATALOGUE` has exactly the 13 expected keys.
- **Unit:** Every entry has `1 <= len(tips) <= 3`.
- **Property (Hypothesis):** For every material in `CATALOGUE`, all tip keys and the name key resolve to
  non-empty strings in all three locales.

### `tests/test_vision.py`

- **Unit:** `classify` returns a valid `ClassificationResult` for a well-formed mock response.
- **Unit:** `classify` returns `None` for malformed JSON or an unknown material value.
- **Unit:** `classify` raises `VisionUnavailable` for a mocked 429 error and for a timeout.
- **Unit:** `decide` returns `None` for `None`, for `UNCLEAR`, and for confidence 0.59; returns the
  material for confidence exactly 0.6.
- **Property (Hypothesis):** for any catalogue key and any confidence in [0, 1], `decide` returns the
  catalogue entry iff confidence ≥ 0.6.
- Mock strategy: inject a fake client object into `Vision` (no network).

### `tests/test_bot.py`

- **Unit:** the photo flow sends `photo.unclear` when `decide` returns `None`.
- **Unit:** the photo flow sends `photo.busy` when `classify` raises `VisionUnavailable`.
- **Unit:** the photo flow sends the correct material reply for a confident result.
- **Unit:** a PDF document gets `photo.bad_file`; a PNG document goes through the photo flow.
- Mock `python-telegram-bot`'s `Update` and `Context` objects using `AsyncMock`.

---

## Dependencies (pinned to compatible versions)

### Runtime
| Package | Min version | Purpose |
|---|---|---|
| `python-telegram-bot` | 21.* | Telegram bot framework |
| `google-genai` | 1.* | Gemini API client |
| `pydantic` | 2.* | Data validation |
| `pydantic-settings` | 2.* | Config from env vars |

### Dev / test
| Package | Purpose |
|---|---|
| `pytest` | Test runner |
| `pytest-asyncio` | Async test support |
| `hypothesis` | Property-based tests |
| `ruff` | Linting and formatting |

---

## Privacy and security notes

- Photo bytes live only in the memory of the handler coroutine; they are not written anywhere.
- Gemini is called with the raw bytes; the SDK does not persist them.
- SQLite stores only `user_id` (Telegram integer) and the language code.
- Logging uses `DEBUG` for anything that could contain user-identifiable data.
