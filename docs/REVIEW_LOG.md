# Review log

Changes made outside Kiro, kept here so the "How we used Kiro" write-up stays honest.

## 2026-11-01 — spec review (before implementation)
Kiro generated `requirements.md`, `design.md` and `tasks.md` for `core-bot`. A second AI assistant
(Claude) reviewed them and the corrections were applied to the spec files by hand: async Gemini client
with `response_schema` and an `UNCLEAR` value, a pure `decide()` function with property-based tests,
a separate "service busy" message for quota errors, image files sent as documents, config that never
fails at import time, `data/qayta.db`, one dotted locale-key style.

## 2026-11-01 — review of Kiro tasks 1–2
Kiro implemented tasks 1–2 (skeleton, config, 4 tests — all pass). Fixes applied by hand:
- `.env.example`: inline `# comments` after `GEMINI_MODEL=` would have produced an empty model name
  if copied to `.env`; comments moved to their own lines and optional values commented out.
- Lint: unused import, import order, long lines, `tmp_path` type hint, fixture return type.

## 2026-11-06 — review of Kiro task 3
Kiro created the locale files, `i18n.py` and its tests (17 tests pass in total). Fix applied by hand:
two unused imports in `tests/test_i18n.py` removed with `ruff --fix`.

## 2026-11-06 — review of Kiro tasks 4–7 (core-bot complete, 62 tests pass)
Fixes applied by hand:
- The bot crashed at startup although all tests passed: `python-telegram-bot` 21 calls
  `asyncio.get_event_loop()`, which raises on Python 3.14. Dependency raised to `>=22.5,<23`.
- `tip.discharge` told users to fully discharge batteries; replaced in all locales with safer advice
  (tape the terminals, do not take it apart).
- Lesson for the next specs: add a startup smoke test, since mocked tests cannot catch this.

## 2026-11-06 — first real run with Telegram and Gemini
- `gemini-2.5-flash` is closed to new users and `gemini-flash-latest` returned 503 (high demand), so the
  default model is now `gemini-flash-lite-latest`. A real structured response works: a screenshot was
  correctly classified as `UNCLEAR`.
- `httpx` logged Telegram URLs containing the bot token at INFO; its logger is now set to WARNING.

## 2026-11-06 — review of the `mini-app` spec
Kiro generated `design.md` and `requirements.md`. A "Review corrections" section was added by hand: `sendData`
only works from a keyboard button, a static site cannot read SQLite, browsers forbid `User-Agent`, most Uzbek
points lack material tags, optional config, keyed hashing, daily point cap, stale prices, location fallback.
- Kiro's first `tasks.md` for `mini-app` did not follow the corrections, so the affected tasks were rewritten by hand
  and the test tasks were made required rather than optional.

## 2026-11-15: language choice (hand change after live test)
Live test: the bot answered only in Uzbek, because a new user defaulted to `uz` and the picker hid behind `/lang`.
Changed by hand: `/start` stores the Telegram `language_code` (uz/ru/en, otherwise uz) on the first visit and
always shows the three-language buttons; the command menu is published in uz, ru and en (`set_my_commands`).
Added `storage.has_lang` and tests (164 pass).
