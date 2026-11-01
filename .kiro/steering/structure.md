---
inclusion: always
---

# Project structure

```
src/qayta/
  __main__.py      # entry point: build the application and start polling
  config.py        # settings from environment
  bot.py           # Telegram handlers only: parse update -> call services -> send reply
  vision.py        # Gemini call + Pydantic schema for the material classification
  materials.py     # material catalogue: names, preparation tips, OSM recycling tags, average weights
  places.py        # Overpass query building, parsing, distance sorting, cache
  impact.py        # per-user counters and landfill-mass estimate
  i18n.py          # loads locales/*.json and formats messages
  storage.py       # SQLite helpers
locales/           # uz.json, ru.json, en.json — identical key sets
webapp/            # Telegram Mini App map (static, GitHub Pages)
tests/             # mirrors src/qayta module names
```

- Handlers in `bot.py` stay thin; logic lives in the service modules so it can be tested without Telegram.
- Add new materials only in `materials.py`; every material needs tips in all three locales.
