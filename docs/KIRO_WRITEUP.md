# How Qayta was built with Kiro

Qayta is a Telegram bot and Telegram Mini App that tells people in Uzbekistan whether an item can be recycled,
how to prepare it, what buyers pay for it, and where to hand it in. It was built for Kiroween 2026
(category: **Frankenstein**: Gemini vision, a Telegram bot, a static Mini App on GitHub Pages, OpenStreetMap
Overpass data and SQLite stitched into one product).

Everything below is what actually happened. Changes made outside Kiro are listed in [`REVIEW_LOG.md`](REVIEW_LOG.md).

## Kiro features we used

| Feature | Used? | How |
|---|---|---|
| Kiro IDE | Yes | All implementation ran in Kiro IDE 1.4 on Windows. |
| Spec-driven development | Yes | Two specs: `core-bot` (22 tasks) and `mini-app` (54 tasks). |
| Steering docs | Yes | `product.md`, `tech.md`, `structure.md`. |
| Property-based testing | Yes | `hypothesis` properties in both specs. |
| Autopilot + permissions | Yes | Autopilot with `permissions.yaml` allow and deny rules. |
| Agent hooks | No | Not needed for this size of project. |
| MCP, powers, custom agents, Kiro CLI/Web/Crew | No | Not used. We list them so the write-up is not inflated. |

## Spec-driven development

1. **Requirements first.** For each spec Kiro generated `requirements.md` (EARS-style acceptance criteria),
   `design.md` (modules, data shapes, error handling, correctness properties) and `tasks.md`.
2. **Review before code.** We reviewed each spec before running it and wrote a "Review corrections" section at the
   top of the spec. Examples from `mini-app`: a Mini App can only call `sendData` when opened from a keyboard
   button; a static site cannot read the bot's SQLite; plain SHA-256 of a Telegram id is reversible by brute force,
   so ids are hashed with HMAC-SHA256 keyed by the bot token; at most 20 items per user per day count towards points;
   prices older than 60 days are labelled "may be outdated".
3. **Run all tasks.** `core-bot` finished 22/22 tasks (62 tests). `mini-app` finished 54/54 tasks (158 tests).
   Every task links back to requirement numbers, so each test traces to an acceptance criterion.

**Compared with vibe coding:** the corrections above would have been bugs found late (or never). Writing them into
the spec once meant Kiro applied them in every task that touched hashing, points or prices. When Kiro's first
`tasks.md` for `mini-app` ignored some corrections, we rewrote those tasks by hand before running them, which was
cheaper than fixing generated code afterwards.

## Steering

- `product.md`: who the users are (Uzbek, Russian and English speakers), tone, and that facts and prices must be
  real, never invented.
- `structure.md`: package layout (`src/qayta`, `tests`, `locales`, `webapp`).
- `tech.md`: Python 3.14, python-telegram-bot 22, google-genai, SQLite, `hypothesis`; plus machine-specific rules.

The steering change with the biggest effect was the machine-specific part of `tech.md`. Our project folder has a
Cyrillic path, and Kiro's shell corrupted it, which wasted credits on path errors. We added a Latin-only junction
(`D:\qayta`) and told Kiro in steering to use relative paths, PowerShell 5.1 syntax (no `&&`) and only
`.venv\Scripts\python.exe`. After that the path errors stopped.

## Property-based testing

Properties from the specs, implemented with `hypothesis`:

- **Points maths identity:** total points always equal counted items plus 5 per approved report.
- **Level is always valid:** any non-negative score maps to a known level key.
- **Distance sort is non-decreasing:** nearby points are always ordered by distance.
- **Report user id is always hashed:** for any integer id, the stored value is the keyed hash, never the raw id.
- **Price lookup is total:** for any material key, including unknown ones, the lookup returns `None` or a complete
  record (price, source, date), never a partial one.
- Core bot: the pure `decide()` function maps any classifier output (including `UNCLEAR` and low confidence) to a
  known material or to "unclear", never to an invalid value.

PBT found nothing dramatic in these small pure functions, but it forced them to be pure and total, which is what
made the bot handlers easy to test with mocks.

## Autopilot and permissions

Kiro paused once during `mini-app`: a sub-agent ran pytest with the global Python, did not find `hypothesis` and
asked us to `pip install`. The project venv already had it. We fixed the cause rather than the symptom:

- steering now says "use `.venv\Scripts\python.exe`, never run `pip install`, do not stop to ask";
- user-level `permissions.yaml` allows the project's test, lint and file commands, denies reading or writing
  `.env`, `git push` and recursive deletes, and asks before any `pip install`.

After that change Kiro completed the remaining 47 tasks in Autopilot without a single prompt.

## What we fixed by hand (and what Kiro could not have known)

- `python-telegram-bot` 21 crashed at startup on Python 3.14 although all mocked tests passed. We raised the
  dependency and added a `--check` startup smoke test to the next spec.
- `httpx` logged Telegram URLs that contain the bot token; its logger is now at WARNING.
- One safety tip told users to fully discharge batteries; it now says to tape the terminals.
- A live test showed the bot always answered in Uzbek for new users; `/start` now uses the Telegram language and
  always shows a three-language picker.

## Results

- 164 tests pass, `ruff` is clean.
- Bot: [@AICiroPRobot](https://t.me/AICiroPRobot). Mini App: <https://sitemaster05.github.io/qayta/>.
- Prices: 9 real buy prices from public OLX.uz ads in Tashkent (October–November 2026), each with its ad ID and
  date. Materials without a clear per-kg price stay empty instead of guessed.
