# Tasks — core-bot

## Task 1 — Project skeleton and `pyproject.toml`

Create the full directory skeleton and `pyproject.toml`.

- [x] Create `src/qayta/__init__.py` (empty, just `__version__ = "0.1.0"`).
- [x] Create `src/qayta/__main__.py` with a `main()` stub that prints "Qayta starting…" (real wiring happens in Task 7).
- [x] Create `tests/__init__.py` (empty).
- [x] Create `tests/conftest.py` with a `pytest.ini`-style `asyncio_mode = "auto"` marker and any shared fixtures.
- [x] Write `pyproject.toml`:
  - `[project]` metadata: name `qayta`, version `0.1.0`, requires-python `>=3.12`.
  - Runtime dependencies: `python-telegram-bot>=21,<22`, `google-genai>=1,<2`, `pydantic>=2,<3`, `pydantic-settings>=2,<3`.
  - `[project.optional-dependencies]` group `dev`: `pytest>=8`, `pytest-asyncio>=0.23`, `hypothesis>=6`, `ruff>=0.4`.
  - `[tool.ruff]` section: `line-length = 110`, `target-version = "py312"`.
  - `[tool.pytest.ini_options]`: `asyncio_mode = "auto"`, `testpaths = ["tests"]`.
  - `[build-system]` using `hatchling`.

**Verification:** `python -m qayta` prints the stub message without errors.

---

## Task 2 — Configuration (`config.py`)

Implement settings loading with `pydantic-settings`.

- [x] Create `src/qayta/config.py` with a `Settings(BaseSettings)` class covering `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, `GEMINI_MODEL` (default `"gemini-2.5-flash"`), `WEBAPP_URL` (default `""`), `DB_PATH` (default `"data/qayta.db"`).
- [x] Add `model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")`.
- [x] Expose `get_settings() -> Settings` cached with `functools.cache`; nothing is validated at import time.
- [x] Verify `.env.example` has all variable names with empty values and one-line comments.
- [x] Tests: importing `qayta.config` works without any environment variables; `get_settings()` raises `ValidationError` when `TELEGRAM_BOT_TOKEN` is missing (use `monkeypatch` and a temporary working directory).

**Verification:** `pytest tests/test_config.py` passes without a `.env` file.

---

## Task 3 — Locale files and `i18n.py`

Create the three locale files and the translation helper.

- [x] Create `locales/uz.json`, `locales/ru.json`, `locales/en.json` with the full dotted key set documented in `design.md` (`cmd.*`, `lang.*`, `photo.*`, all 13 `mat.*` names, all `tip.*` keys). Values must be real, translated text — not placeholders. Uzbek uses the Latin script.
- [x] Create `src/qayta/i18n.py`:
  - Load all three files at module import; raise `FileNotFoundError` early if any is missing.
  - Implement `t(key: str, lang: str, **kwargs: object) -> str` with English fallback.
- [x] Create `tests/test_i18n.py`:
  - Unit test: known key returns correct string.
  - Unit test: unknown language falls back to English.
  - Property test (`@given`): for every key in `uz.json`, formatting with the correct placeholder names does not raise. Use `hypothesis.strategies.text()` for placeholder values.

**Verification:** `pytest tests/test_i18n.py` passes; all three property tests shrink and pass.

---

## Task 4 — Material catalogue (`materials.py`)

Implement the catalogue and its tests.

- [x] Create `src/qayta/materials.py`:
  - Define `Material` as a frozen dataclass with fields: `key`, `name_i18n`, `recyclable_uz`, `tips`, `osm_tag`, `avg_weight_g`.
  - Define `CATALOGUE: dict[str, Material]` with all 13 entries. Assign realistic `avg_weight_g` values (document sources as inline comments). Assign correct `osm_tag` values.
  - `recyclable_uz` means "commonly accepted by collection points in Uzbekistan"; add a short README note that this is general guidance, not a legal rule.
- [x] Create `tests/test_materials.py`:
  - Unit test: `CATALOGUE` contains exactly the 13 expected keys.
  - Unit test: every entry satisfies `1 <= len(tips) <= 3`.
  - Property test: for every material key, both `name_i18n` and each tip key resolve to non-empty strings in all three locales (call `t()` inside the test).

**Verification:** `pytest tests/test_materials.py` passes.

---

## Task 5 — Storage (`storage.py`)

Implement the SQLite helper for language preferences.

- [x] Create `src/qayta/storage.py`:
  - Accept `db_path: str = "data/qayta.db"` in an `init_db(db_path)` function and create the parent folder if missing.
  - Create the `user_language` table on first call.
  - Implement `get_lang(user_id: int) -> str` (default `"uz"`) and `set_lang(user_id: int, lang: str) -> None`.
  - Keep the connection as a module-level singleton (thread-local or single connection for the polling process).
- [x] Add unit tests in `tests/test_bot.py` (or a separate `tests/test_storage.py`) using an in-memory SQLite DB (`":memory:"`):
  - `get_lang` returns `"uz"` for an unknown user.
  - `set_lang` then `get_lang` round-trips correctly.

**Verification:** `pytest tests/` passes.

---

## Task 6 — Vision (`vision.py`)

Implement the Gemini photo classification and its tests.

- [x] Create `src/qayta/vision.py`:
  - Define the `MaterialKey` enum (catalogue keys + `UNCLEAR`) and `ClassificationResult(BaseModel)` with `material: MaterialKey`, `confidence: float = Field(ge=0.0, le=1.0)`, `reason: str`.
  - Define `VisionUnavailable(Exception)` and module-level `CLASSIFICATION_PROMPT: str` (lists the allowed keys, explains when to answer `UNCLEAR`).
  - Implement `class Vision` that creates ONE `google.genai.Client` in `__init__` and has `async def classify(image_bytes, mime_type) -> ClassificationResult | None` using `await client.aio.models.generate_content(...)` with `response_mime_type="application/json"`, `response_schema=ClassificationResult`, `temperature=0`, inside `asyncio.timeout(30)`.
    - 429/quota, timeout and network errors → raise `VisionUnavailable`.
    - Malformed JSON or schema mismatch → return `None`.
  - Implement pure `decide(result) -> Material | None` with `CONFIDENCE_THRESHOLD = 0.6`.
- [x] Create `tests/test_vision.py` (inject a fake client, no network):
  - Valid response → `ClassificationResult`; malformed JSON → `None`; mocked 429 and timeout → `VisionUnavailable`.
  - `decide`: `None`, `UNCLEAR`, confidence 0.59 → `None`; confidence exactly 0.6 → the material.
  - Property test (`@given`): for any catalogue key and confidence in [0, 1], `decide` returns the entry iff confidence ≥ 0.6.

**Verification:** `pytest tests/test_vision.py` passes with all Gemini calls mocked.

---

## Task 7 — Bot handlers (`bot.py`) and wiring (`__main__.py`)

Implement all Telegram handlers and wire everything together.

- [x] Create `src/qayta/bot.py`:
  - Import `settings`, `storage`, `i18n`, `materials`, `vision`.
  - Implement `get_user_lang(user_id: int) -> str` helper.
  - Implement `start_handler`, `help_handler` using `t()`.
  - Implement `lang_handler` — sends `InlineKeyboardMarkup` with three buttons (`callback_data="lang_uz"`, `"lang_ru"`, `"lang_en"`).
  - Implement `lang_callback_handler` — parses callback data, calls `storage.set_lang`, answers the query with a confirmation.
  - Implement a shared `classify_and_reply(update, context, image_bytes, mime_type)`:
    1. `await update.message.reply_chat_action(ChatAction.TYPING)`.
    2. `result = await vision.classify(...)`; on `VisionUnavailable` reply `t("photo.busy", lang)`.
    3. `material = decide(result)`; if `None`, reply `t("photo.unclear", lang)`.
    4. Otherwise send `t("photo.result", ...)` built from `mat.<KEY>`, `photo.recyclable` / `photo.not_recyclable` and the tips.
  - `photo_handler` downloads the largest `PhotoSize` into memory and calls the helper.
  - `image_file_handler` accepts documents with `image/jpeg`, `image/png`, `image/webp` up to 10 MB and calls the helper; `other_file_handler` replies `photo.bad_file`.
  - Implement `register_handlers(app: Application) -> None` that adds all handlers to the app.
- [x] Update `src/qayta/__main__.py`: call `get_settings()` (exit with a clear message on missing variables), `init_db(settings.db_path)`, create one `Vision` and store it in `app.bot_data`, call `register_handlers()`, start polling.
- [x] Add tests in `tests/test_bot.py` (mock Update and Context with `AsyncMock`):
  - `photo.unclear` when `decide` returns `None`; `photo.busy` when `classify` raises `VisionUnavailable`; the material reply for a confident result.
  - A PDF document gets `photo.bad_file`; a PNG document goes through the photo flow.
  - `lang_callback_handler` calls `storage.set_lang` with the correct arguments.

**Verification:** `pytest tests/` passes; `ruff check src/ tests/` reports no errors; `python -m qayta` starts successfully with valid env vars.
