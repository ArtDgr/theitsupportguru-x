# The IT Support Guru — Headless X Publisher (Faceless, No Buffer)

Automated X pipeline for `@theitsupprtguru` — 4×/day Mon-Fri faceless headless, **same logic as Instagram** (`FacelessStudio/src/x-*`) but via **Substack-style Python headless stack** (no Buffer, no browser).

## Stack (mirrors `theitsupportguru-substack`)
- **No Buffer.** Ayrshare free API (`AYRSHARE_API_KEY`, 20/mo) posts to X from GitHub Actions. Same free-runner model as Substack's Email-to-Post (whitelisted, no fingerprint).
- **Fixed AEST (UTC+10)** + jitter (Substack `publish.py:48` pattern) — defeats cron-bot heuristic.
- **30d Telegram gate** then `AUTO_PUBLISH=1` — human APPROVE/REJECT first 12, then fully headless.

## Schedule (AEST, mirrors Instagram `config.x.postingTimes`)
| Slot | Local AEST | UTC Cron | Pillar rotation |
|---|---|---|---|
| 0 | 06:00 | 20:00 prior day | DAILY RED FLAG |
| 1 | 12:00 | 02:00 | TECH MYTHBUSTER |
| 2 | 17:00 | 07:00 | IT GURU SECRETS |
| 3 | 20:00 | 10:00 | MICRO GUIDE |
| 4* | Fri 18:00 | Fri 08:00 | FRIDAY GADGET FOCUS |

*Single daily build at 05:30 AEST (19:30 UTC) synthesizes 4 tweets, then Ayrshare `scheduleDate` spreads them — same as Instagram's daily manifest.

## Quick Start (local dry-run)
1. Copy `.env.example` → `.env`, fill `OPENAI_API_KEY / GEMINI_API_KEY / TAVILY_API_KEY / AYRSHARE_API_KEY / TELEGRAM_*`
2. `pip install -r requirements.txt`
3. `python src/ingest.py && python src/score.py && python src/enrich.py && python src/synthesize.py && python src/qa.py`
4. `SKIP_SLEEP=1 python src/publish.py` → writes `out/tweets.json` + Telegram draft (dry-run if no `AYRSHARE_API_KEY`)

## Deploy Headless (GitHub Actions)
- Push to GitHub, add repo **Secrets** (`OPENAI_API_KEY, GEMINI_API_KEY, TAVILY_API_KEY, AYRSHARE_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, AUTO_PUBLISH=0`)
- Cron `.github/workflows/publish.yml:4` fires daily 19:30 UTC (05:30 AEST Mon-Fri) then jitters to 06:12-06:27 AEST per Substack anti-bot.
- 30d gate: Telegram shows 4 drafts with APPROVE/REJECT. Reply APPROVE or `python src/approve.py approve drafts/2026-xx-xx-xxx.md`
- After 12 approved (~30d), set Secret `AUTO_PUBLISH=1` → fully headless (no human, no Buffer).

## Anti-Bot Design (from Substack)
- **Jitter** `publish.py:48` random 2h12m-2h27m so publish second varies.
- **Variance** random pillar rotation, subject variants, `User-Agent: TheITSupportGuru-X/1.0`.
- **Weekly ramp** same as IG: cap 80/mo (~4×20 weekdays), random gate Max 12 → 80 for X volume.

## Structure
`config/sources.yaml` (7 niches, 48 feeds, mirrors `FacelessStudio/config.json` niches) | `prompts/analyst_system.md` (X 280-char pillars) | `src/` pipeline | `drafts/*.md` | `out/tweets.json`

## Why No Buffer?
Buffer free = 10 queued + API limits, and X via Buffer still needs Professional IG link. Ayrshare free = 20/mo, 1 key, no channel Professional gate, whitelisted IP (GitHub runner) — same as Substack's whitelisted Email secret.

Verify: `python -m py_compile src/*.py`

