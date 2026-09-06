# Little DMV

[![refresh events](https://github.com/opoo-em/little-dmv/actions/workflows/refresh.yml/badge.svg)](https://github.com/opoo-em/little-dmv/actions/workflows/refresh.yml)

A phone-first dashboard of kid-friendly events across Montgomery County MD and DC. Built for a specific family — filters age and cost to what actually fits.

**Live:** https://opoo-em.github.io/little-dmv/

## Status

**Phase 1 (dashboard + schema): DONE, deployed.**
**Phase 2 (real data sources): IN PROGRESS.** Pipeline scaffold + 4 HTML scrapers landed. iCal endpoints for MCPL / Montgomery Parks / Kennedy Center / Smithsonian pending URL verification (see `docs/sources.md`). Dummy events still in `events.json` — will be replaced on the next successful pipeline run.

## Repo structure

```
├── index.html              — the dashboard (reader of events.json)
├── favicon.svg             — rainbow heart, Lisa Frank vibes
├── data/
│   └── events.json         — source of truth (dummy data for now)
├── scripts/
│   ├── main.py             — pipeline orchestrator (writes data/events.json)
│   ├── sources.yaml        — registry of iCal feeds and HTML scrapers
│   ├── ical_fetch.py       — iCal fetching + RRULE expansion
│   ├── filter.py           — age filter (~1-3yr overlap rule)
│   ├── distance.py         — haversine + banding (reads HOME_LAT/HOME_LNG env)
│   ├── normalize.py        — raw event → canonical schema
│   ├── add_event.py        — manual add flow ("I saw a sign for X")
│   ├── requirements.txt
│   └── scrapers/           — per-site HTML scrapers (Schema.org JSON-LD first)
│       ├── jsonld.py       — shared JSON-LD Event extractor
│       ├── butlers.py
│       ├── glen_echo.py
│       ├── nbm.py
│       └── kidfriendly_dc.py
├── .github/workflows/
│   └── refresh.yml         — Sunday 8am ET cron + manual trigger
├── docs/
│   ├── decisions.md        — settled design decisions + WHY (read before proposing changes)
│   └── sources.md          — Phase 2 attack plan: source inventory + priorities + investigation notes
└── README.md               — this file
```

## Architecture

Two-layer, source-of-truth separation:

- **`data/events.json`** — canonical event data. Any surface that displays events reads from this file.
- **`index.html`** — the dashboard. A reader of `events.json`. Fetches at page load, renders the filtered list.
- **Future surfaces** (digest email, gcal push, printed sheet, whatever) — additional readers of the same JSON, never owners.

## Event schema (v1)

```json
{
  "id": "unique-slug",
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "end": "HH:MM or null",
  "name": "Event name",
  "venue": "Full venue name",
  "distance_mi_range": "0-5 | 6-10 | 11-15 | 16-20 | 20+",
  "cost_type": "free | paid",
  "cost_label": "Free | $10 child | etc.",
  "place": "indoor | outdoor",
  "age": "human-readable age range",
  "age_match_reason": "why this passed the age filter (for debugging)",
  "description": "One-paragraph description",
  "url": "Source URL",
  "source": "which pipeline surfaced this",
  "added_at": "ISO 8601 UTC",
  "updated_at": "ISO 8601 UTC",
  "expires_at": "ISO 8601 UTC or null"
}
```

Top level of `events.json` also carries `last_updated` (ISO 8601) and `schema_version` (int).

## Filter rules (baked into scraper — not user-facing)

- **Age:** must include ~1-3yr (toddler). Excludes hard-only-babies (e.g. "hatchlings 4mo") and hard-only-older (5+, kindergarten+, elementary). See `docs/decisions.md` for the exact rule.
- **Cost:** no ceiling. All costs included in the JSON; users toggle free/paid in the UI.

## UI filters (user-controlled)

- **Date range:** Today / Tomorrow / This Weekend / Next 7 Days / Next 14 Days / Custom
- **Place:** All / Indoor / Outdoor
- **Cost:** All / Free / Paid

Default view: This Weekend, All, All.

## Distance calculation

Distance is **banded** (0-5 / 6-10 / 11-15 / 16-20 / 20+ miles), never precise, to preserve privacy in the public repo. Reference home coordinates are stored as a GitHub Secret (`HOME_LAT`, `HOME_LNG`), never committed. The scraper reads the secret, computes distance per event, writes only the band to `events.json`. Repo readers never see raw coordinates or exact distances.

## Docs — start here

- **`docs/decisions.md`** — settled design decisions with reasoning. **Read this before proposing UI/schema changes.** Includes explicit guidance from Em on when to bring new ideas vs when NOT to relitigate.
- **`docs/sources.md`** — Phase 2 attack plan. Every source classified by priority and feed type. Investigation notes go here as each source is wired.

## Pipeline

Run manually:
```
pip install -r scripts/requirements.txt
export HOME_LAT=... HOME_LNG=...        # optional; without them, distance is 'unknown'
python -m scripts.main                  # writes data/events.json
python -m scripts.main --dry-run        # print to stdout instead
python -m scripts.main --keep-dummy     # merge with existing manual events
python -m scripts.main --only butlers-orchard,glen-echo-park   # subset run
```

Runs automatically Sunday 12:00 UTC (8am ET) via `.github/workflows/refresh.yml`.
Manual trigger from the Actions tab any time.

Add a one-off event you spotted on a sign:
```
python -m scripts.add_event                 # interactive prompts
```

## Phase 2 roadmap

Rough order of attack (from `docs/sources.md`):

1. **iCal-having sources** — MCPL, Montgomery Parks, Kennedy Center, Smithsonian. *Endpoints still need verification from a network that can reach them.* See `docs/sources.md` → Investigation notes.
2. **HTML scrapers for high-volume sources** — Butler's Orchard, Glen Echo, National Building Museum, KidFriendly DC. *Landed, using Schema.org JSON-LD extraction.*
3. **Newsletter / manual for the long tail** — Congressional Plaza signage, farmers market seasonal quirks. Use `scripts/add_event.py`.

Also pending in Phase 2:
- **Home coordinates** need to be added as GitHub Secrets `HOME_LAT` and `HOME_LNG` before distance banding is meaningful.
- **On-demand refresh via Claude Code** — Em says "refresh little dmv", I run `python -m scripts.main` locally and push. Also the "Run workflow" button in the Actions tab.
