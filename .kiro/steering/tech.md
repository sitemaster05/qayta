---
inclusion: always
---

# Tech stack and rules

- Python 3.12, `src/` layout, package `qayta`. Run with `python -m qayta`.
- Telegram: `python-telegram-bot` v21+ (async, long polling).
- AI vision: Google Gemini via the `google-genai` SDK, model name from config (default `gemini-flash-lite-latest`).
  Always request **structured JSON output** and validate it with a Pydantic v2 model; if validation fails or
  confidence < 0.6, treat the result as "unclear".
- Collection points: Overpass API over `httpx` (async). Respect the Overpass usage policy: one request at a
  time, a descriptive User-Agent, a 25-second timeout, and cache results per rounded location
  (3 decimals) for 24 hours in SQLite.
- Storage: SQLite via the standard `sqlite3` module (impact counters and the Overpass cache only).
- Configuration: environment variables loaded from `.env` (`TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, ...).
  Never commit secrets; `.env.example` lists the variable names with empty values.
- Mini App: a static page in `webapp/` (HTML + Leaflet + OpenStreetMap tiles) published with GitHub Pages;
  it receives the material and coordinates through URL parameters and queries Overpass directly.

## Running commands on this machine
- Open and run the project from `D:\qayta` (a Latin-only path). Do not investigate paths: the terminal
  already opens in the project root, so use relative paths only, without `cd`, `Push-Location` or `PYTHONPATH`.
- Always use the project virtual environment, which has all dependencies:
  `.venv\Scripts\python.exe -m pytest tests\test_x.py -q` and `.venv\Scripts\python.exe -m ruff check .`
  Do not use the global `python`.
- All dependencies, including `hypothesis`, `pytest-asyncio` and `ruff`, are already installed in `.venv`.
  Never run `pip install`. If an import fails, you used the wrong Python: rerun with `.venv\Scripts\python.exe`.
- Work through all tasks without stopping to ask; stop only if a test still fails after two fixes.
- The shell is Windows PowerShell 5.1: `&&` does not work. Run commands one at a time or separate them with `;`.

## Quality
- Tests with `pytest` and `pytest-asyncio`; **property-based tests with `hypothesis`** for pure logic
  (distance calculation, material-to-OSM-tag mapping, impact maths, translation completeness).
- External services (Telegram, Gemini, Overpass) are always mocked in tests; tests must run offline.
- `ruff` for linting and formatting, line length 110.
- Every module has type hints; keep functions small and readable.
- Log with the `logging` module; never log tokens, photos or exact user locations.
