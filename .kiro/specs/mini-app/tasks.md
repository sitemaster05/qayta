# Implementation Plan: mini-app

## Overview

Tasks build from the inside out: pure-logic modules first (`impact.py`, `places.py`), then storage
extensions, then the bot additions, and finally the static Mini App. Each task is self-contained and
integrates into the previous step so no orphaned code is left in place.

---

## Tasks

- [x] 1. Extend `config.py` and `storage.py`
  - [x] 1.1 Add an optional `admin_user_id: int = 0` field to `Settings` in `config.py` (0 disables `/review`; a missing value must not stop the bot); add `ADMIN_USER_ID` to `.env.example` as a commented-out line.
    - _Requirements: 15.1, 15.2, 15.3_
  - [x] 1.2 Add `CREATE TABLE IF NOT EXISTS` statements for `reports`, `impact`, and `overpass_cache` tables to `storage.init_db()` using the schemas in `design.md`.
    - _Requirements: 6.4, 9.3, 10.4_
  - [x] 1.3 Write unit tests for the new config field (missing `ADMIN_USER_ID` gives 0) and for the three new tables being created in an in-memory DB.
    - _Requirements: 15.1, 15.2_

- [x] 2. Implement `impact.py`
  - [x] 2.1 Create `src/qayta/impact.py` with `hash_user_id`, `total_points`, `get_level`, `LEVELS`, `increment_items`, `increment_reports`, `get_stats`, and `get_leaderboard` as specified in `design.md`, following Review corrections 7, 8 and 12: `hash_user_id` is HMAC-SHA256 keyed with the bot token, at most 20 items per user per day count towards points (store the day and daily count), levels are locale keys, and the leaderboard returns an alias such as "Recycler #A1F3". Use `storage._require_conn()` for DB access.
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_
  - [x] 2.2 Write property test for `total_points` identity
    - **Property 2: Points maths identity**
    - **Validates: Requirements 10.1**
  - [x] 2.3 Write property test for `get_level` always valid
    - **Property 3: Level is always a valid string**
    - **Validates: Requirements 10.2**
  - [x] 2.4 Write property test for `hash_user_id` correctness
    - **Property 5: Report user_id is always stored hashed** (hash_user_id variant)
    - **Validates: Requirements 10.3**
  - [x] 2.5 Write unit tests for `increment_items`/`increment_reports` upsert semantics and `get_leaderboard` ordering using in-memory SQLite.
    - _Requirements: 10.4, 10.5_

- [x] 3. Implement `places.py`
  - [x] 3.1 Create `src/qayta/places.py` with `haversine`, `sort_by_distance`, `build_overpass_query`, and `fetch_nearby` as specified in `design.md`, following Review corrections 3 and 4: query `nwr["amenity"="recycling"]` and `nwr["shop"="scrap"]` with `out center`; try overpass-api.de, then the maps.mail.ru mirror; return points without `recycling:*` tags too, marked `materials_known: false` and listed after points known to accept the material. `fetch_nearby` checks `overpass_cache`, calls Overpass via `httpx.AsyncClient`, writes result to cache.
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_
  - [x] 3.2 Write property test for `sort_by_distance` non-decreasing
    - **Property 1: Distance sort is non-decreasing**
    - **Validates: Requirements 9.1**
  - [x] 3.3 Write unit tests for `haversine` (identity at 0,0; ~111 km per degree), `build_overpass_query` contains osm_tag, cache hit path, cache miss path, and Overpass failure returning empty list. Mock `httpx` throughout.
    - _Requirements: 9.2, 9.3, 9.4, 9.5_

- [x] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement `reports.py`
  - [x] 5.1 Create `src/qayta/reports.py` with `add_report`, `get_pending_reports`, `approve_report`, and `reject_report` as specified in `design.md`. `add_report` calls `impact.hash_user_id` and stores `user_id_hash`, never the raw ID.
    - _Requirements: 6.4, 7.3, 7.4_
  - [x] 5.2 Write unit tests for the insert/approve/reject lifecycle: verify `status` transitions, `reviewed_at` is set on review, and that `user_id_hash != str(user_id)`.
    - _Requirements: 6.4, 7.3, 7.4_
  - [x] 5.3 Write property test for `hash_user_id` in reports: for any integer user_id, the stored value equals `impact.hash_user_id(user_id)` (HMAC) and never contains the raw id.
    - **Property 5: Report user_id is always stored hashed**
    - **Validates: Requirements 6.4**

- [x] 6. Add locale keys to all three locale files
  - [x] 6.1 Add all new keys listed in Requirement 16.1 to `locales/uz.json`, `locales/ru.json`, and `locales/en.json` with real translated values (not placeholders). Keys: `map.title`, `map.choose_material`, `map.no_points`, `map.route`, `map.verified_on`, `map.no_location`, `map.open_osm`, `report.received`, `report.invalid`, `report.point_form`, `report.price_form`, `review.none_pending`, `review.approved`, `review.rejected`, `stats.result`, `stats.level`, `stats.items`, `stats.reports`, `stats.points`, `impact.open_map_button`, `cmd.review`, `cmd.stats`, `cmd.report`, `level.beginner`, `level.recycler`, `level.champion`, `level.legend`, `price.outdated`, `map.materials_unknown`.
    - _Requirements: 16.1, 16.2_

- [x] 7. Extend `bot.py` with new handlers
  - [x] 7.1 Implement `web_app_data_handler`: parse `update.message.web_app_data.data` as JSON, validate required fields for `type="point"` or `type="price"`, call `reports.add_report`, reply with `report.received`; on validation failure reply `report.invalid`.
    - _Requirements: 6.4, 6.5, 6.6_
  - [x] 7.2 Implement `review_handler` (`/review` command): check `user_id == settings.admin_user_id`; if not admin return silently. Fetch pending reports, send one message per report with `[Approve ✅ | Reject ❌]` inline keyboard (`callback_data="review_approve_{id}"` / `"review_reject_{id}"`). Reply `review.none_pending` when queue is empty.
    - _Requirements: 7.1, 7.2, 7.5_
  - [x] 7.3 Implement `review_callback_handler`: parse action and report ID; call `reports.approve_report` or `reports.reject_report`; on approve also call `impact.increment_reports` for the reporter's hash; edit message to show `review.approved` or `review.rejected`.
    - _Requirements: 7.3, 7.4_
  - [x] 7.4 Implement `stats_handler` (`/stats` command): hash user ID, call `impact.get_stats`, reply with formatted `stats.result`.
    - _Requirements: 11.1, 11.2_
  - [x] 7.5 Implement `location_handler`: store `(lat, lon)` in `context.user_data["last_location"]` (in-memory only, not DB).
    - _Requirements: 8.4_
  - [x] 7.6 Extend `classify_and_reply`: after a successful classification, load `webapp/data/prices.json` once (cache in `context.bot_data`), look up best price for the material, append price line when available (add `price.outdated` when the date is older than 60 days); only when `WEBAPP_URL` starts with `https://`, append a `WebAppInfo` inline button `"🗺 Open Map"` pointing to `{WEBAPP_URL}#map?material={KEY}`; call `impact.increment_items(user_id_hash)`. Where `context.user_data["last_location"]` is set, call `places.fetch_nearby` and append nearest point name.
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - [x] 7.6a Implement `report_handler` (`/report`): when `WEBAPP_URL` is https, show a `ReplyKeyboardMarkup` with `KeyboardButton(web_app=WebAppInfo(url=f"{WEBAPP_URL}#report"))`, because `sendData` works only from a keyboard button. `stats_handler` also shows the top-10 leaderboard and, when `WEBAPP_URL` is set, a Mini App button with `#me?items=..&reports=..&rank=..`.
    - _Requirements: Review corrections 1, 2_
  - [x] 7.7 Register all new handlers in `register_handlers`: `web_app_data_handler`, `report_handler`, `review_handler`, `review_callback_handler`, `stats_handler`, `location_handler`.
    - _Requirements: 6.3, 7.1, 11.1_
  - [x] 7.8 Write unit tests for all new handlers using `AsyncMock`. Test: `web_app_data_handler` calls `reports.add_report` and replies `report.received`; invalid payload replies `report.invalid`. `review_handler` is silent for non-admin, sends message for admin. `review_callback_handler` calls approve/reject and increments reports on approve. `stats_handler` replies with stats. `classify_and_reply` appends map button.
    - _Requirements: 6.5, 6.6, 7.2, 8.2_
  - [x] 7.9 Write property test for price lookup: for any material key (including keys not in prices.json), the lookup function returns None or a complete dict with all required fields.
    - **Property 4: Price lookup returns None or a complete record**
    - **Validates: Requirements 8.1**

- [x] 8. Extend `__main__.py`
  - [x] 8.1 Add `--check` flag: when present, validate settings, call `storage.init_db(":memory:")` to verify schema creation, parse `webapp/data/points.json` and `webapp/data/prices.json` as JSON arrays, print success and exit 0; exit 1 with a descriptive message on any failure.
    - _Requirements: 17.1, 17.2, 17.3_
  - [x] 8.2 Set the bot menu button via `await app.bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="🗺 Qayta", web_app=WebAppInfo(url=settings.webapp_url)))` in the `post_init` callback (skip unless `webapp_url` starts with `https://`).
    - _Requirements: 14.1_

- [x] 9. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Create curated data files
  - [x] 10.1 Create `webapp/data/points.json` containing an empty JSON array `[]`.
    - _Requirements: 13.1_
  - [x] 10.2 Create `webapp/data/prices.json` containing an empty JSON array `[]`.
    - _Requirements: 13.2_

- [x] 11. Build the Mini App — shell and i18n
  - [x] 11.1 Create `webapp/index.html`: single-page shell with bottom nav bar (four `<button data-tab="...">` elements), a `<main id="tab-content">` area, and CDN `<script>` tags for Leaflet, followed by local script tags for `i18n.js`, `app.js`, `map.js`, `prices.js`, `me.js`.
    - _Requirements: 1.1, 1.2, 1.6_
  - [x] 11.2 Create `webapp/style.css` with CSS custom properties for the dark-green design system (colors, radius, tab height). Ensure minimum 375 px usability and tap targets ≥ 44 × 44 px.
    - _Requirements: 1.4, 1.5_
  - [x] 11.3 Create `webapp/i18n.js` with `STRINGS` object containing `uz`, `ru`, and `en` sub-objects for all keys defined in Requirement 16.1, plus tab labels. Implement `t(key, params)` function with `localStorage` language preference and fallback to `"uz"`.
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 12. Build the Mini App — `app.js` and tab router
  - [x] 12.1 Create `webapp/app.js`: call `Telegram.WebApp.ready()` and `Telegram.WebApp.expand()`; apply `themeParams` to CSS custom properties; implement tab router that shows/hides tab content on bottom-bar button clicks; implement language switcher that persists choice in `localStorage` and re-renders; implement URL-hash routing so `#map?material={KEY}` navigates to Map tab and passes `KEY` to `map.js`.
    - _Requirements: 1.3, 1.7, 2.3_

- [x] 13. Build the Mini App — Map tab (`map.js`)
  - [x] 13.1 Create `webapp/map.js`: on Map tab activation, use Telegram `LocationManager` when available, then `navigator.geolocation`, then let the user pick Tashkent, Ohangaron or Samarkand or tap the map. Initialise a Leaflet map on that position; fetch `data/points.json` and merge with Overpass results (curated records take precedence by `id`; try overpass-api.de, then the maps.mail.ru mirror; never set a `User-Agent` header). Points known to accept the material come first; others are shown with `map.materials_unknown`. Popups show name, materials, phone, hours, verified-date badge, best price with `price.outdated` when older than 60 days, and a route link.
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [x] 14. Build the Mini App — Scan and Prices tabs
  - [x] 14.1 Add Scan-tab content to `app.js` or as a separate module: render a short localised guide and a button that calls `Telegram.WebApp.close()` so that the user sends the photo in the chat.
    - _Requirements: 3.1, 3.2_
  - [x] 14.2 Create `webapp/prices.js`: fetch `data/prices.json`; group rows by material using CATALOGUE key order; render an HTML table with columns Material, Point, Price (so'm/kg), Source, Date; show "—" and a hint to send `/report` for missing prices; add `price.outdated` for prices older than 60 days.
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 15. Build the Mini App — Me tab (`me.js`)
  - [x] 15.1 Create `webapp/me.js`: read `items`, `reports` and `rank` from the URL hash set by the bot; display items sorted, approved reports, total points, a localised level badge and level thresholds, mirroring `getLevel` and `totalPoints` from `impact.py`. Without hash values show an invitation to send `/stats`. No leaderboard file: the leaderboard lives in `/stats`.
  - [x] 15.2 Add the `#report` screen: forms for a new point and a new price that call `Telegram.WebApp.sendData(JSON.stringify(...))`, shown only when opened from the `/report` keyboard button.
    - _Requirements: Review correction 1_
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [x] 16. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass and `ruff check src/ tests/` reports no errors. Run `python -m qayta --check` and confirm exit code 0. Ask the user if questions arise.

---

## Notes

- Each task references specific requirements for traceability.
- Checkpoints ensure incremental validation.
- All Telegram, Gemini, and Overpass calls must remain mocked in tests.
- The Mini App JS (`webapp/`) is not covered by Python tests; it is tested manually in Telegram.
- `webapp/data/points.json` and `webapp/data/prices.json` start as empty arrays and are populated by
  the admin after reviewing community reports.
- The `--check` smoke test can be run in CI to catch config or data-file regressions early.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "2.1", "3.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "2.4", "2.5", "3.2", "3.3"] },
    { "id": 3, "tasks": ["5.1", "6.1"] },
    { "id": 4, "tasks": ["5.2", "5.3", "7.1", "7.2", "7.3", "7.4", "7.5", "7.6"] },
    { "id": 5, "tasks": ["7.7", "7.8", "7.9", "8.1", "8.2"] },
    { "id": 6, "tasks": ["10.1", "10.2"] },
    { "id": 7, "tasks": ["11.1", "11.2", "11.3"] },
    { "id": 8, "tasks": ["12.1"] },
    { "id": 9, "tasks": ["13.1", "14.1", "14.2"] },
    { "id": 10, "tasks": ["15.1"] }
  ]
}
```
