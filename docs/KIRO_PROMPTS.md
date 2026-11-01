# Работа в Kiro — пошагово

Запросы для Kiro даны на английском: копируй их в чат Kiro целиком, от `>` до конца блока.
После каждого этапа напиши Claude «готово»: он проверит код, запустит тесты и даст следующий шаг.

## Подготовка (один раз)
1. Обнови Kiro: в PowerShell `winget upgrade --id Amazon.Kiro`.
2. Запроси 4 000 кредитов (см. `D:\Работа\docs\KIROWEEN_PLAN.md`, шаги 2–4). Без них хватит только на начало.
3. Открой папку проекта: Kiro → File → Open Folder → `D:\Работа\hackathons\qayta`.
4. В панели Kiro (значок призрака слева) проверь раздел **Steering**: там уже три файла —
   product, tech, structure. Kiro будет учитывать их в каждом ответе.

## Этап 1. Спецификация ядра бота
В чате Kiro выбери режим **Spec** и вставь:

> Create a spec named `core-bot` for Qayta as described in the steering docs. Scope of this spec:
> project skeleton (`pyproject.toml`, `src/qayta`, `tests`), configuration from `.env`, i18n with
> `locales/uz.json`, `ru.json`, `en.json` and a `/lang` command, the `/start` and `/help` messages, the
> material catalogue in `materials.py`, and the photo flow: the user sends a photo, `vision.py` asks Gemini
> for structured JSON (material, confidence, short reason), and the bot replies with the material name,
> whether it is recyclable in Uzbekistan and 1–3 preparation tips. Low confidence must produce a polite
> request for a clearer photo. Do not implement collection points or the map yet — they are separate specs.
> Include property-based tests (hypothesis) for the catalogue and for translation completeness.

Kiro по очереди покажет `requirements.md`, `design.md`, `tasks.md`. Прочитай каждый файл
и нажимай **Approve / Move to next phase**. Если что-то непонятно, пришли Claude скриншот или текст.
Потом открой `tasks.md` и запускай задачи кнопкой **Start task** сверху вниз.

## Этап 2. Хуки (автоматизация)
Панель Kiro → **Agent Hooks** → «+». Создай три хука, описав их своими словами (можно вставить текст):

1. > When a Python file under `src/` is saved, run `pytest` for the matching test module and `ruff check`
   > on the changed file. If something fails, explain the failure and propose a fix.
2. > When any file in `locales/` is saved, check that uz.json, ru.json and en.json have exactly the same keys
   > and the same `{placeholders}`; list anything missing.
3. (ручной запуск) > Update the "How we used Kiro" section of README.md with what was built since the last run:
   > specs completed, hooks that fired, and notable fixes.

## Этап 3. Пункты приёма
Режим **Spec**:

> Create a spec named `nearby-points`. When the user shares a location (Telegram location message or the
> "Share location" button offered after a classification), query the Overpass API for recycling points
> within 5 km that accept the classified material (map materials to OSM `recycling:*` tags in
> `materials.py`), sort by distance, and reply with the 5 nearest: name or "Recycling point", distance,
> accepted materials and a Google/OSM map link. Cache results in SQLite for 24 hours per rounded location.
> If there are none, say so honestly and link to the OpenStreetMap guide for adding a point.
> Follow the Overpass usage policy from the tech steering doc. Mock Overpass in tests and add
> property-based tests for the distance function and the cache key rounding.

## Этап 4. Карта в Telegram (Mini App)
> Create a spec named `map-mini-app`: a static page in `webapp/` (HTML, CSS, Leaflet, OSM tiles, no build
> step) opened from the bot with a WebApp button. It reads `material`, `lat`, `lon` and `lang` from the URL,
> shows the user and nearby recycling points with popups, uses Telegram theme colours, and works on a
> 375-px phone screen. Add a "Recycled" visual style: green accents and a small Qayta logo.

## Этап 5. Вклад пользователя
> Create a spec named `impact`: count items sorted per user and estimate the mass kept out of landfill using
> average item weights from `materials.py`. Add `/stats` with a friendly summary in the user's language.
> Store only a hashed user id and counters. Property-based tests for the maths.

## Что делать, если кредиты кончаются
Пиши Claude: он подскажет, какие задачи можно объединить. Не запускай задачи «на всякий случай».
