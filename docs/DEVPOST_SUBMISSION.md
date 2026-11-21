# Devpost submission: Qayta (Kiroween 2026)

Copy each block into the matching Devpost field.

## Project name
Qayta

## Elevator pitch (tagline)
Snap a photo of your waste in Telegram: Qayta says if it is recycled in Uzbekistan, how to prepare it, what buyers pay and where to take it.

## Category
Frankenstein

## Links
- GitHub (public, MIT): https://github.com/sitemaster05/qayta
- Working app: https://t.me/AICiroPRobot (Telegram bot) and https://sitemaster05.github.io/qayta/ (Mini App)
- Demo video: https://youtu.be/fZ69Y1ZP4is
- Devpost: https://devpost.com/software/qayta (submitted 2026-11-18)
- Social Blitz post: https://www.instagram.com/p/Df4q0AvDEWo/
- Blog post: https://telegra.ph/How-I-built-a-recycling-bot-for-Uzbekistan-with-Kiro-specs-11-18 (text in docs/BLOG_POST.md)

## Testing instructions for judges
Open https://t.me/AICiroPRobot in Telegram and press Start. Pick a language (O'zbek, Русский, English).
Send a photo of one item (a bottle, a box, a can). Use the menu button "🗺 Qayta" to open the Mini App
(Map, Prices, Me tabs). `/stats` shows your points, `/report` lets you suggest a new point or price.
No login is needed. The bot runs on the author's computer, so if it does not answer, please try again later
or run it locally: `pip install -e ".[dev]"`, fill `.env` from `.env.example`, `python -m qayta`.

## About the project

### Inspiration
In Uzbekistan a lot of paper, cardboard and metal could be sold to buyers, but people do not know what is
accepted, how to prepare it, or what it is worth. Information lives in scattered OLX ads and Telegram groups,
mostly in one language. We wanted one place inside the app everyone already uses: Telegram.

### What it does
- Send a photo: Gemini identifies the material (13 categories, or "unclear"), says whether it is recycled in
  Uzbekistan, and gives preparation tips.
- Uzbek, Russian and English; a new user gets their Telegram language and can switch any time.
- A Telegram Mini App with a recycling map from OpenStreetMap, a prices table and a personal impact tab.
- Real buyer prices with source and date; prices older than 60 days are marked as possibly outdated.
- Points for sorting (max 20 items per day count), community reports of new points and prices, reviewed by an
  admin with `/review` before they go live. Telegram ids are stored only as HMAC-SHA256 hashes.

### How we built it
With the Kiro IDE and spec-driven development: two specs (`core-bot`, 22 tasks; `mini-app`, 54 tasks), three
steering docs, property-based tests with `hypothesis`, and Autopilot with `permissions.yaml` rules. Stack:
Python 3.14, python-telegram-bot 22, Google Gemini (google-genai), SQLite, OpenStreetMap Overpass, Leaflet,
vanilla JS, GitHub Pages. Details: docs/KIRO_WRITEUP.md.

### Challenges we ran into
- All mocked tests passed but the bot crashed on Python 3.14 (an old python-telegram-bot); we added a startup
  smoke test (`--check`).
- A Cyrillic project path confused the agent's shell; a Latin-only junction plus steering rules fixed it.
- An Autopilot run paused because a sub-agent used the global Python; one steering line and a permissions file
  let the remaining 47 tasks run without prompts.
- Real prices: few buyers publish per-kg prices, so we only show prices that have a clear figure, source and date.

### Accomplishments that we're proud of
164 passing tests, a working bot and Mini App in three languages, and no invented data: every price links to a
dated public ad.

### What we learned
Reviewing the spec before running tasks is the cheapest place to fix design mistakes. Steering is the place for
machine-specific rules, not just style.

### What's next for Qayta
Phone-verified prices from collection points in Tashkent and Ohangaron, a curated list of points with consent,
and PET and metal prices.

## Built with
python, python-telegram-bot, gemini, google-genai, sqlite, hypothesis, pytest, javascript, leaflet,
openstreetmap, overpass-api, github-pages, telegram-mini-apps, kiro

## How Kiro was used (field for judges)
See docs/KIRO_WRITEUP.md in the repository (specs, steering, property-based testing, Autopilot and permissions,
and the list of hand fixes).
