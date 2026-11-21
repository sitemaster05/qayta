# How I built a recycling bot for Uzbekistan with Kiro specs

*This post is written as part of the Kiroween 2026 hackathon.*

In Tashkent you can sell clean white paper for about 3,000 som per kilogram and cardboard for around 1,800. Most people never do, because nobody tells them what is accepted, how to prepare it or who is buying. That information lives in scattered OLX ads and Telegram groups, usually in one language.

So for Kiroween I built **Qayta** ("again" in Uzbek): a Telegram bot and Mini App. You send a photo of an item, and Qayta says what material it is, whether it is recycled in Uzbekistan, how to prepare it, what buyers pay and where to take it. It speaks Uzbek, Russian and English.

- Bot: https://t.me/AICiroPRobot
- Mini App: https://sitemaster05.github.io/qayta/
- Code: https://github.com/sitemaster05/qayta
- Demo: https://youtu.be/fZ69Y1ZP4is

## Specs before code

I did not start by chatting with an agent. I started with two Kiro specs: `core-bot` (photo classification, tips, languages) and `mini-app` (map, prices, points, community reports). For each one Kiro wrote requirements, a design and a task list.

The most useful hour of the project was reading those specs before running anything. I found design problems that would have been bugs later:

- A Telegram Mini App can only send data back to the bot when it is opened from a keyboard button.
- A static page on GitHub Pages cannot read the bot's SQLite database.
- Hashing a Telegram id with plain SHA-256 is reversible by brute force, so ids are hashed with HMAC keyed by the bot token.
- Without a cap, one person could farm points by sending the same photo all day, so only 20 items a day count.

I wrote these as "Review corrections" at the top of the spec. After that, Kiro applied them in every task that touched hashing, points or prices. Fixing a sentence in a spec is much cheaper than fixing the same mistake in five generated files.

## Steering for a very local problem

My work folder has a Cyrillic name. The agent's shell kept mangling one letter in the path, and every mangled path cost credits. The fix was not clever code. It was a Latin-only folder junction and three lines in the steering file `tech.md`: use relative paths, PowerShell 5.1 syntax, and only the project's virtual environment. The path errors stopped.

## Property-based tests

The design listed correctness properties, and Kiro turned them into `hypothesis` tests. For example, the distance sort of nearby points is never out of order, a stored report never contains a raw Telegram id, and the price lookup returns either nothing or a complete record with a source and a date. These tests did not find dramatic bugs, but they kept the core functions small and pure, which made the bot handlers easy to test.

## Autopilot, and the one time it stopped

The `mini-app` spec has 54 tasks. I pressed "Run all tasks" in Autopilot. At task 2.2 Kiro paused and asked me to `pip install hypothesis`: a sub-agent had run the tests with the global Python, not the project's environment, which already had everything.

Instead of answering the same question again and again, I fixed the cause: one more steering line ("use `.venv`, never run `pip install`, do not stop to ask") and a `permissions.yaml` with allow rules for the project's test and file commands and deny rules for secrets, `git push` and recursive deletes. Kiro then finished the remaining 47 tasks without a single prompt.

## What Kiro could not know

Some things only a live run shows:

- All mocked tests passed, yet the bot crashed at startup on Python 3.14 because of an old Telegram library. Now there is a `--check` smoke test.
- A library logged request URLs that contain the bot token. That logger is now quieter.
- The first live test showed the bot answering everyone in Uzbek. Now `/start` uses the Telegram language and shows a three-language picker.
- One battery tip was unsafe and was rewritten.

I keep every hand change in a review log in the repository, so the story of "what the agent did" stays honest.

## Real prices, not made-up ones

The prices tab only shows numbers I could trace: 9 buyer prices from public OLX ads in Tashkent from October and November 2026, each with its ad ID and date. I could not find a clear per-kilogram price for PET bottles, glass or steel, so those rows stay empty instead of guessed. Prices older than 60 days are marked as possibly outdated.

## Results and what is next

164 tests pass, the bot and Mini App work in three languages, and the specs, steering and task history are all in the `.kiro` folder of the repository. Next I want phone-verified prices from collection points in Tashkent and Ohangaron and a curated map of points, added only with their consent.

The main lesson for me: with Kiro, the time I spent thinking in the spec saved far more time than the code it generated.

*Aleksandr Kim, Ohangaron, Uzbekistan. Written for Kiroween 2026.*
