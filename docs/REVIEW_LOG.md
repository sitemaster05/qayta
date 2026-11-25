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

## 2026-11-13 – 2026-11-15: mini-app implementation run (54/54 tasks, 158 tests)
- Kiro ran "Run all tasks" in Autopilot. It paused once at task 2.2: a sub-agent ran pytest with the global
  Python, did not find `hypothesis` and asked for `pip install`. The project `.venv` already had everything.
  Fix by hand: steering `tech.md` now says "use `.venv\Scripts\python.exe`, never `pip install`, do not stop to ask",
  and user-level `permissions.yaml` allow rules cover the project's test and file commands (deny rules for
  `.env`, `git push`, recursive deletes). After that Kiro finished the remaining 47 tasks without prompts.
- Hand review after the run: tests and ruff pass, Mini App checked in a 375 px browser viewport in three languages.

## 2026-11-18: first real prices
`webapp/data/prices.json` filled with 9 prices from public OLX.uz buy ads in Tashkent (22 Oct – 15 Nov 2026):
white paper, books and newspapers, cardboard, aluminium frames. Each record names the ad ID and date; ranges keep
the lower bound. No PET, glass or steel price had a clear per-kg figure, so those stay empty rather than guessed.

## 2026-11-19: hosting without the author's PC
The bot ran on the author's computer, but the project must stay testable until judging ends (29.01.2027).
Added by hand: webhook mode (`run()` in `__main__.py`, `python-telegram-bot[webhooks]`, secret token derived from the
bot token), `render.yaml` for a free Render web service, and a `keep-alive` GitHub Action. Long polling stays the
default when no https URL is set. 169 tests pass.

## 2026-11-19: health page for uptime pings
GitHub's scheduled Actions ran only about once an hour, so the free Render service still fell asleep. An external
cron (cron-job.org) now pings the service every 10 minutes. PTB's built-in webhook server answered 404 on `/`, which
such monitors treat as a failure, so `run()` now serves its own small tornado app: `GET /` returns `ok`, and
`POST /telegram` checks the secret header (403 otherwise) before queuing the update. 170 tests pass.

## 2026-11-21: live demo video
Devpost asked for a demo that shows the project working on its device: the first video was built from screenshots.
New video https://youtu.be/fZ69Y1ZP4is is a live screen recording of Telegram Desktop: /start and the language picker,
a photo of bottles answered by Gemini (PET Plastic #1, recyclable, preparation tips), then the Mini App map, prices and
My impact. The submission's demo video URL now points to it.

## 2026-11-25: agent hooks
Added three Kiro agent hooks in `.kiro/hooks/` (v2 JSON format): run the test suite when a `.py` file in `src/` or
`tests/` is saved, run the i18n tests when a locale file is saved, and run `python -m qayta --check` when Mini App data
changes. All use the project venv. Kiro's log on 25 Nov shows `hooks.reload.loaded {"read":3,"registered":3}`.
