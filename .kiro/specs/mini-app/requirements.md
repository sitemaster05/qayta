# Requirements Document

## Introduction

This document derives testable requirements from the `mini-app` design. It covers the Telegram Mini App
(`webapp/`), the curated data files, the community report flow, bot additions (price line, map button,
menu button, `/review`, `/stats`, `/check`), and the Me-tab impact system. Collection-point lookup via
Overpass is included as a backend service consumed by both the Mini App and the bot.

Out of scope: core photo classification (covered by `core-bot`), nearby-points deep integration (covered
by `nearby-points`).

---

## Glossary

- **Mini App**: The Telegram Mini App served from `WEBAPP_URL` (GitHub Pages). Opened inside Telegram.
- **Bot**: The Python `python-telegram-bot` process (`src/qayta/`).
- **Admin**: The Telegram user whose integer ID matches `ADMIN_USER_ID` in config.
- **Curated point**: A collection-point record in `webapp/data/points.json`, reviewed and committed by
  the Admin.
- **Curated price**: A price record in `webapp/data/prices.json`, reviewed and committed by the Admin.
- **Report**: A pending community submission stored in the SQLite `reports` table.
- **user_id_hash**: The SHA-256 hex digest of the string representation of the Telegram integer user ID.
- **CATALOGUE**: The dict defined in `materials.py`, keyed by material identifier strings.
- **Overpass_Cache**: The `overpass_cache` SQLite table used by `places.py`.
- **Impact_DB**: The `impact` SQLite table used by `impact.py`.
- **Report_DB**: The `reports` SQLite table used by `reports.py`.

---

### Review corrections (take precedence over everything else in this spec)

1. **Reports open from a keyboard button.** `Telegram.WebApp.sendData` works only when the Mini App is launched
   from a reply-keyboard button, not from the menu button or an inline button. Add a `/report` command that shows a
   `KeyboardButton(web_app=...)` opening `#report`. The report forms live on that screen. In the tabs, "Report"
   links explain this and send the user to `/report` instead of calling `sendData`.
2. **No backend for the Me tab.** The site is static and cannot read SQLite. The bot passes display values in the URL
   hash of the buttons it creates, e.g. `#me?items=3&reports=1&rank=7`. Without values the Me tab invites the
   user to send `/stats`. The leaderboard is shown by `/stats` in the bot; remove `data/leaderboard.json`.
3. **Overpass.** Browsers forbid setting `User-Agent`: do not set it in `map.js`; `places.py` keeps it. Try
   `https://overpass-api.de/api/interpreter`, then `https://maps.mail.ru/osm/tools/overpass/api/interpreter`.
   Query `nwr["amenity"="recycling"]` and `nwr["shop"="scrap"]` with `out center`, never `shop=second_hand`.
4. **Do not hide points with unknown materials.** Most Uzbek points have no `recycling:*` tags. Show them with a
   "materials unknown, call first" label below the points that are known to accept the material.
5. **`ADMIN_USER_ID` is optional** (default 0 = `/review` disabled). A missing value must not stop the bot.
6. **`WEBAPP_URL` is optional.** If it is empty or not `https://`, omit every Mini App button and the menu button.
7. **Hashing.** Plain SHA-256 of a Telegram id can be reversed by brute force. Use HMAC-SHA256 keyed with the bot
   token and do not claim it is irreversible. The leaderboard shows a friendly alias such as "Recycler #A1F3".
8. **Fair points.** At most 20 sorted items per user per day count towards points.
9. **Stale prices.** A price older than 60 days is labelled "may be outdated". Example values in this document are
   illustrative only: `points.json` and `prices.json` ship as `[]`.
10. **Location.** The Map tab uses Telegram `LocationManager` when available, then `navigator.geolocation`, then lets the
    user pick a city (Tashkent, Ohangaron, Samarkand) or tap the map.
11. **Scan tab.** A Mini App cannot send a photo to the bot: the Scan tab shows a short guide and a button
    that calls `Telegram.WebApp.close()` so that the user sends the photo in the chat.
12. **Localised levels.** Level names come from the locale files and `i18n.js`, not hard-coded English strings.

## Requirements

### Requirement 1: Static Mini App shell

**User Story:** As a Telegram user, I want to open a polished Mini App inside Telegram so that I can
access the map, prices, and my stats without leaving the app.

#### Acceptance Criteria

1. THE Mini App SHALL be a single HTML page at `webapp/index.html` that loads without a build step.
2. THE Mini App SHALL display a persistent bottom navigation bar with four tabs: Scan, Map, Prices, Me.
3. THE Mini App SHALL call `Telegram.WebApp.ready()` and `Telegram.WebApp.expand()` on load.
4. THE Mini App SHALL apply CSS custom properties for the dark-green design system and override them with
   `Telegram.WebApp.themeParams` values when available.
5. THE Mini App SHALL be usable at a minimum viewport width of 375 px; all interactive tap targets SHALL
   be at least 44 × 44 px.
6. THE Mini App SHALL load Leaflet from CDN and all other JS from local files in `webapp/`.
7. WHEN the URL fragment contains `#map?material={KEY}`, THE Mini App SHALL navigate to the Map tab and
   pre-select `KEY` in the material filter.

---

### Requirement 2: Internationalisation in the Mini App

**User Story:** As a user, I want the Mini App to display text in my preferred language (Uzbek, Russian,
or English) so that I can understand all labels and messages.

#### Acceptance Criteria

1. THE Mini App SHALL include a `webapp/i18n.js` file containing all user-visible strings for `uz`, `ru`,
   and `en` in a single JS object.
2. THE `i18n.js` key set SHALL mirror the locale key naming convention used in `locales/*.json`
   (`tab.*`, `map.*`, `report.*`, `stats.*`, etc.).
3. WHEN a user selects a language in the Mini App, THE Mini App SHALL persist the choice in
   `localStorage` under the key `qayta_lang` and re-render all visible strings immediately.
4. THE Mini App SHALL default to `"uz"` when no language preference is stored.

---

### Requirement 3: Scan tab

**User Story:** As a user, I want to see a clear Scan tab so that I understand photos must be sent via
the bot rather than through the Mini App.

#### Acceptance Criteria

1. THE Scan_Tab SHALL display a localised placeholder message instructing the user to open the bot and
   send a photo, because the camera is not accessible inside a Mini App.
2. THE Scan_Tab SHALL include a button or link that opens the Telegram bot chat when tapped.

---

### Requirement 4: Map tab

**User Story:** As a user, I want to see nearby recycling collection points on a map so that I can find
the closest place to drop off a specific material.

#### Acceptance Criteria

1. WHEN the Map tab is activated, THE Map_Tab SHALL request the user's geolocation via the browser
   Geolocation API.
2. WHEN geolocation is granted, THE Map_Tab SHALL display a Leaflet map centred on the user's position
   with OpenStreetMap tiles and a "© OpenStreetMap contributors" attribution.
3. THE Map_Tab SHALL fetch `webapp/data/points.json` and merge it with live Overpass results, with
   curated records taking precedence over Overpass records when both have the same `id`.
4. THE Map_Tab SHALL show markers only for points that accept the material selected in the material
   filter; when no material is selected, all points SHALL be shown.
5. WHEN a marker is tapped, THE Map_Tab SHALL display a popup containing: point name, accepted materials,
   phone number (if available), opening hours (if available), a "verified on YYYY-MM-DD" badge for
   curated points, the best known price for the selected material (if any), and a route link using a
   `geo:{lat},{lon}` URI.
6. THE Map_Tab Overpass query SHALL include a descriptive `User-Agent` header:
   `"Qayta-bot/1.0 (+https://github.com/qayta)"`.
7. IF geolocation is denied or unavailable, THEN THE Map_Tab SHALL display a localised message
   (`map.no_location`) and still show curated points without distance sorting.

---

### Requirement 5: Prices tab

**User Story:** As a user, I want to see current recycling prices by material so that I know what my
waste is worth before going to a collection point.

#### Acceptance Criteria

1. THE Prices_Tab SHALL fetch `webapp/data/prices.json` and render a table with columns: Material, Point,
   Price (so'm/kg), Source, Date.
2. WHEN no price record exists for a material, THE Prices_Tab SHALL display a "—" placeholder and a
   "Report price" link for that row.
3. THE Prices_Tab SHALL display the source and date alongside every price so users can judge freshness.
4. THE Prices_Tab SHALL never display an invented or estimated price; all prices MUST originate from
   `prices.json` or be absent.

---

### Requirement 6: Community report flow

**User Story:** As a user, I want to report a new collection point or update a price so that the
community data stays accurate.

#### Acceptance Criteria

1. THE Mini App SHALL provide a "Report a point" form collecting: name, latitude, longitude, accepted
   materials (multi-select from CATALOGUE), phone (optional), hours (optional).
2. THE Mini App SHALL provide a "Report a price" form collecting: point (select from known points),
   material (select from CATALOGUE), price in so'm/kg.
3. WHEN a form is submitted, THE Mini App SHALL call `Telegram.WebApp.sendData(JSON.stringify({type, ...fields}))`.
4. WHEN the Bot receives `web_app_data`, THE Bot SHALL hash the sender's `user_id` with SHA-256 and store
   `user_id_hash`, `type`, `payload` (JSON), `status = 'pending'`, and `created_at` (ISO-8601 UTC) in
   Report_DB. The raw Telegram `user_id` SHALL NOT be stored.
5. WHEN a report is stored, THE Bot SHALL reply to the user with a localised confirmation (`report.received`).
6. IF the `web_app_data` payload is missing required fields, THEN THE Bot SHALL reply with
   `report.invalid` and SHALL NOT insert a row into Report_DB.

---

### Requirement 7: /review admin command

**User Story:** As the Admin, I want to review pending community reports and approve or reject them so
that only verified data reaches users.

#### Acceptance Criteria

1. WHEN the `/review` command is received from the Admin user, THE Bot SHALL fetch all pending rows from
   Report_DB and send one Telegram message per report containing the payload and an inline keyboard with
   `[Approve ✅ | Reject ❌]` buttons.
2. WHEN `/review` is received from a non-Admin user, THE Bot SHALL NOT reply (silent rejection).
3. WHEN the Admin taps "Approve", THE Bot SHALL set `status = 'approved'` and `reviewed_at` for that
   report row, call `impact.increment_reports` for the reporter's `user_id_hash`, and edit the message to
   show `review.approved`.
4. WHEN the Admin taps "Reject", THE Bot SHALL set `status = 'rejected'` and `reviewed_at`, and edit the
   message to show `review.rejected`.
5. WHEN there are no pending reports, THE Bot SHALL reply with `review.none_pending`.

---

### Requirement 8: Price line and map button in classification reply

**User Story:** As a user, after the bot classifies my photo I want to immediately see the best known
price for that material and a button to open the map, so I can act on the result right away.

#### Acceptance Criteria

1. WHEN a photo is classified successfully, THE Bot SHALL load `webapp/data/prices.json` and append the
   best (highest) verified price for the identified material to the reply, formatted as
   `"💰 Best price: {price} so'm/kg ({source}, {date})"`. IF no price exists, the line SHALL be omitted.
2. WHEN a photo is classified successfully, THE Bot SHALL append an inline button labelled
   `"🗺 Open Map"` that opens the Mini App at `{WEBAPP_URL}#map?material={KEY}`.
3. WHEN a photo is classified successfully, THE Bot SHALL call `impact.increment_items(user_id_hash)`.
4. WHERE the user has shared a location in the current session (stored in `context.user_data`), THE Bot
   SHALL also append the name and distance of the nearest collection point that accepts the material.

---

### Requirement 9: places.py — distance sorting and Overpass cache

**User Story:** As a developer, I want a `places.py` module that provides sorted nearby points with a
24-hour SQLite cache so that the bot makes minimal Overpass requests.

#### Acceptance Criteria

1. THE `places.py` Module SHALL expose a `sort_by_distance(points, origin_lat, origin_lon)` pure
   function that returns a new list with a `distance_m` key on each entry, sorted ascending by distance.
2. THE `places.py` Module SHALL expose a `haversine(lat1, lon1, lat2, lon2)` pure function returning
   distance in metres.
3. WHEN `fetch_nearby` is called and a valid cache entry exists for the rounded location and material key
   (younger than 24 hours), THE `places.py` Module SHALL return the cached result without querying
   Overpass.
4. WHEN `fetch_nearby` is called and no valid cache entry exists, THE `places.py` Module SHALL query
   Overpass with a `User-Agent` header and a 25-second timeout, parse the response, write it to
   Overpass_Cache, and return the sorted list.
5. IF the Overpass request fails (timeout or HTTP error), THEN THE `places.py` Module SHALL log a warning
   and return an empty list.
6. THE `places.py` Module's Overpass query SHALL only issue one request at a time (the single-process
   polling loop guarantees this; no additional locking is required).

---

### Requirement 10: impact.py — counters and levels

**User Story:** As a user, I want my recycling activity tracked so that I can see my impact and earn
level badges.

#### Acceptance Criteria

1. THE `impact.py` Module SHALL implement `total_points(items_sorted, approved_reports)` as
   `items_sorted + 5 * approved_reports`.
2. THE `impact.py` Module SHALL define four levels: Beginner (0–9 points), Recycler (10–49),
   Champion (50–99), Legend (100+). `get_level(points)` SHALL return exactly one of these four strings.
3. THE `impact.py` Module SHALL implement `hash_user_id(user_id: int) -> str` using
   `hashlib.sha256(str(user_id).encode()).hexdigest()`.
4. THE `impact.py` Module SHALL persist `items_sorted` and `approved_reports` per `user_id_hash` in
   Impact_DB using upsert semantics so that calling `increment_items` twice adds 2, not resets to 1.
5. THE `impact.py` Module SHALL expose `get_leaderboard(limit: int = 10)` returning the top `limit` rows
   ordered by total points descending, each row containing `user_id_hash`, `points`, and `level`.

---

### Requirement 11: /stats command

**User Story:** As a user, I want to see my personal recycling stats in the bot so that I know my impact
without opening the Mini App.

#### Acceptance Criteria

1. WHEN the `/stats` command is received, THE Bot SHALL call `impact.get_stats(user_id_hash)` and reply
   with a localised message (`stats.result`) showing: items sorted, approved reports, total points,
   and level badge.
2. WHEN a user has no recorded activity, THE Bot SHALL reply with zero counts and "Beginner" level.

---

### Requirement 12: Me tab

**User Story:** As a user, I want a Me tab in the Mini App showing my stats, level badge, and the
leaderboard so that I feel motivated to sort more waste.

#### Acceptance Criteria

1. THE Me_Tab SHALL display the user's items sorted, approved reports, total points, and level badge.
2. THE Me_Tab SHALL display the top-10 leaderboard using `user_id_hash` (truncated to 8 characters) as
   the display identifier.
3. THE Me_Tab SHALL display the level thresholds so users know how many more points they need to level up.
4. THE Me_Tab SHALL NOT display any real names, Telegram usernames, or profile photos.

---

### Requirement 13: Curated data files

**User Story:** As the Admin, I want curated data files in the repository so that the Mini App always has
a valid data source even when Overpass is unavailable.

#### Acceptance Criteria

1. THE Repository SHALL contain `webapp/data/points.json` as a valid JSON array (may be empty).
2. THE Repository SHALL contain `webapp/data/prices.json` as a valid JSON array (may be empty).
3. WHEN a curated point is committed, each entry SHALL contain `id`, `name`, `lat`, `lon`, `materials`,
   `source`, and `verified_date` fields.
4. WHEN a curated price is committed, each entry SHALL contain `point_id`, `material`,
   `price_som_per_kg`, `source`, and `date` fields.
5. THE Bot and Mini App SHALL never invent or interpolate prices; a missing price SHALL be represented as
   absent from `prices.json`.

---

### Requirement 14: Menu button and deep links

**User Story:** As a user, I want a persistent menu button on the bot and inline map buttons after
classification so that I can reach the Mini App with one tap.

#### Acceptance Criteria

1. THE Bot SHALL set a `MenuButtonWebApp` pointing to `WEBAPP_URL` so that the Mini App button appears
   in the Telegram chat input area.
2. WHEN a photo is classified successfully, THE Bot SHALL include an inline `WebAppInfo` button
   `"🗺 Open Map"` that opens `{WEBAPP_URL}#map?material={KEY}`.

---

### Requirement 15: config.py addition

**User Story:** As a developer, I want `ADMIN_USER_ID` in the config so that the review command can
safely identify the admin.

#### Acceptance Criteria

1. THE `Settings` Class SHALL include an `admin_user_id: int` field read from the `ADMIN_USER_ID`
   environment variable.
2. IF `ADMIN_USER_ID` is missing, THEN the Bot SHALL exit with a clear error message at startup.
3. THE `.env.example` file SHALL list `ADMIN_USER_ID` with an empty value and a short comment.

---

### Requirement 16: Locale additions

**User Story:** As a developer, I want all three locale files to contain the new keys for the Mini App
and impact features so that no user-visible string is hard-coded.

#### Acceptance Criteria

1. THE Files `locales/uz.json`, `locales/ru.json`, and `locales/en.json` SHALL each gain the following
   keys: `map.title`, `map.choose_material`, `map.no_points`, `map.route`, `map.verified_on`,
   `map.no_location`, `map.open_osm`, `report.received`, `report.invalid`, `report.point_form`,
   `report.price_form`, `review.none_pending`, `review.approved`, `review.rejected`, `stats.result`,
   `stats.level`, `stats.items`, `stats.reports`, `stats.points`, `impact.open_map_button`,
   `cmd.review`, `cmd.stats`.
2. ALL three locale files SHALL have identical key sets after the additions (the property-based i18n test
   already enforces this).

---

### Requirement 17: Startup smoke test

**User Story:** As a developer, I want a `--check` flag that validates the environment so that I can
confirm a deployment is healthy without starting polling.

#### Acceptance Criteria

1. WHEN `python -m qayta --check` is run with all required environment variables set and valid data
   files, THE Bot SHALL validate settings, initialise the database schema, parse `points.json` and
   `prices.json`, and exit with code 0.
2. IF any required environment variable is missing, THEN `python -m qayta --check` SHALL exit with
   code 1 and print a descriptive error message.
3. IF `points.json` or `prices.json` is not valid JSON, THEN `python -m qayta --check` SHALL exit with
   code 1 and print a descriptive error message.

---

### Requirement 18: Tests

**User Story:** As a developer, I want comprehensive tests for all new modules and handlers so that
regressions are caught before deployment.

#### Acceptance Criteria

1. THE Test Suite SHALL include `tests/test_places.py` with unit tests for `haversine`,
   `sort_by_distance`, `build_overpass_query`, and cache hit/miss paths; all Overpass calls SHALL be
   mocked with `httpx`.
2. THE Test Suite SHALL include `tests/test_impact.py` with unit tests for `total_points`, `get_level`
   boundary conditions, and storage round-trips using an in-memory SQLite database.
3. THE Test Suite SHALL include `tests/test_reports.py` with unit tests for the insert/approve/reject
   lifecycle and the `user_id_hash` verification.
4. `tests/test_bot.py` SHALL be extended with tests for `web_app_data_handler`, `review_handler`
   (admin guard), `review_callback_handler`, `stats_handler`, and the map-button addition to
   `classify_and_reply`.
5. THE Test Suite SHALL include property-based tests (Hypothesis) for `sort_by_distance`,
   `total_points`, `get_level`, price lookup, and `hash_user_id`.
6. ALL tests SHALL run fully offline; no live Telegram, Gemini, or Overpass calls are permitted.
