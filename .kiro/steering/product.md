---
inclusion: always
---

# Product: Qayta

*Qayta* is Uzbek for "again / once more". Qayta is a Telegram bot (plus a Telegram Mini App map) that answers
two questions people in Uzbekistan and Central Asia ask before throwing something away:

1. **Can this be recycled, and how do I prepare it?** The user sends a photo; the bot names the material
   (PET #1, HDPE #2, PP #5, glass, paper, cardboard, aluminium/steel, batteries, e-waste, textiles,
   organic, mixed/non-recyclable) and gives 1–3 short preparation steps (rinse, remove cap, flatten).
2. **Where can I hand it in?** The user shares a location; the bot lists the nearest real collection
   points from OpenStreetMap (`amenity=recycling` and recycling shops) that accept that material,
   with distance and a map link. If none are near, it says so honestly and invites the user to add the
   point to OpenStreetMap.

It also keeps a personal impact counter: items sorted and an estimated mass kept out of landfill, using
average item weights that are documented in the code and README.

## Audience
Residents of Uzbek cities (Tashkent, Ohangaron, Samarkand) and anyone in the region with Telegram, which is
the dominant messenger there. Many users are not tech-savvy: replies must be short, friendly, and clear.

## Languages
Uzbek (Latin script) is the default, then Russian and English. The user can switch with /lang.
All user-facing text lives in translation files, never hard-coded in handlers.

## Principles
- Honest answers: when the photo is unclear or confidence is low, ask for another photo instead of guessing.
- Never invent collection points; every point comes from OpenStreetMap data with attribution
  "© OpenStreetMap contributors".
- Privacy: photos are processed in memory and never stored; locations are not stored, only the impact counter.
- Hackathon category: **Frankenstein** — Telegram + multimodal AI vision + OpenStreetMap/Overpass +
  Telegram Mini App map stitched into one helpful app.

## Product direction (updated 2026-11-06)
Tagline: **"Find out what your waste is worth, and put Uzbekistan's recycling on the map."**
OpenStreetMap lists only about 40 recycling and scrap points for the whole of Uzbekistan, so Qayta does not only
read the map, it fills it in.

- **Value first:** after a photo the bot shows the material, the verified price per kg and the nearest buyer.
- **Honest data:** prices and points come only from verified records with a source and a date. Never invent
  or estimate a price; when none is known, say so.
- **Community map:** users report a point or a price; the owner reviews it; approved points are added to
  OpenStreetMap by a person, with the licence respected.
- **Mini App:** a polished Telegram Mini App with four tabs (Scan, Map, Prices, Me) in Uzbek, Russian and English.
- **Motivation without crypto:** points, levels and a leaderboard for sorted items and verified reports.
  No tokens, wallets, blockchain or money rewards: points have no cash value.
