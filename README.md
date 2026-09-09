# Little DMV

[![refresh events](https://github.com/opoo-em/little-dmv/actions/workflows/refresh.yml/badge.svg)](https://github.com/opoo-em/little-dmv/actions/workflows/refresh.yml) [![test](https://github.com/opoo-em/little-dmv/actions/workflows/test.yml/badge.svg)](https://github.com/opoo-em/little-dmv/actions/workflows/test.yml)

A phone-first dashboard of kid-friendly events across Montgomery County MD and DC. Built for a specific family — filters age and cost to what actually fits.

**Live:** https://opoo-em.github.io/little-dmv/

## Status

**Phase 1 (dashboard + schema): DONE, deployed.**
**Phase 2 (real data sources): LIVE.** MCPL + Smithsonian iCal feeds are pulling; 7 per-site HTML scrapers plus a Rockville fallback are wired (Butler's Orchard, National Building Museum, National Children's Museum, Smithsonian National Zoo, Pike & Rose, Puppet Co Tiny Tots, Montgomery Parks, City of Rockville). Kennedy Center, Glen Echo, Bethesda Row, and KidFriendly DC are deliberately skipped — see `docs/decisions.md` for each ruling. Dummy data has been replaced. See `docs/sources.md` for current wiring.

## Repo structure

```
├── index.html              — the dashboard (reader of events.json)
├── favicon.svg             — rainbow heart, Lisa Frank vibes
├── data/
│   ├── events.json         — canonical events (rewritten each pipeline run)
│   └── seasonal.json       — manually-curated annual events
├── scripts/
│   ├── main.py             — pipeline orchestrator (writes data/events.json)
│   ├── sources.yaml        — registry of iCal feeds and HTML scrapers
│   ├── ical_fetch.py       — iCal fetching + RRULE expansion
│   ├── seasonal.py         — reads data/seasonal.json into the pipeline
│   ├── filter.py           — age filter (~1-3yr overlap rule)
│   ├── distance.py         — haversine + banding (reads HOME_LAT/HOME_LNG env)
│   ├── weather.py          — NWS weather stamp for outdoor events
│   ├── normalize.py        — raw event → canonical schema
│   ├── add_event.py        — manual add flow ("I saw a sign for X")
│   ├── requirements.txt
│   ├── tests/              — pytest suite
│   └── scrapers/           — per-site HTML scrapers
│       ├── base.py         — shared HTTP client
│       ├── jsonld.py       — shared JSON-LD Event extractor
│       ├── butlers.py
│       ├── nbm.py
│       ├── national_childrens_museum.py
│       ├── national_zoo.py
│       ├── pike_and_rose.py
│       ├── puppetco.py
│       ├── montgomery_parks.py
│       └── rockville.py
├── .github/workflows/
│   └── refresh.yml         — Sunday 8am ET cron + manual trigger
├── docs/
│   ├── decisions.md        — settled design decisions + WHY (read before proposing changes)
│   ├── sources.md          — source inventory: what's wired, what's skipped, what's next
│   ├── scraper-prompts.md  — copy-paste prompts for claude.ai when we need per-site parsers
│   ├── scraper-prompt-responses/  — claude.ai deliveries, one file per scraper
│   └── handoff-*.md        — session handoffs (read newest first)
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
python -m scripts.main --only butlers-orchard,national-zoo     # subset run
```

Runs automatically Sunday 12:00 UTC (8am ET) via `.github/workflows/refresh.yml`.
Manual trigger from the Actions tab any time.

Add a one-off event you spotted on a sign:
```
python -m scripts.add_event                 # interactive prompts
```

## Phase 2 status

Current state (as of the last handoff — see `docs/handoff-*.md` for the newest one):

1. **iCal:** MCPL (Toddler + Baby feed) and Smithsonian (Trumba) are wired and pulling. Montgomery Parks has no iCal endpoint despite the plugin shape — scraper wired for the Featured Events carousel only. Kennedy Center retired (age mismatch).
2. **HTML scrapers:** Butler's Orchard, National Building Museum, National Children's Museum, Smithsonian National Zoo, Pike & Rose, Puppet Co Tiny Tots, Montgomery Parks, and City of Rockville. Most use per-site parsers rather than JSON-LD (the sites don't emit it). See `docs/decisions.md` for per-source rulings.
3. **Skipped:** Glen Echo (age mismatch), Bethesda Row (no real events calendar), KidFriendly DC (no structured events on site — replaced by newsletter copy-paste flow via `scripts/add_event.py`).

Still pending:
- **Home coordinates** need to be set as GitHub Secrets `HOME_LAT` and `HOME_LNG` for distance banding to be meaningful.
- **On-demand refresh via Claude Code** — Em says "refresh little dmv", I trigger the Actions workflow or run `python -m scripts.main` and push.
- **Newsletter copy-paste flow** for KidFriendly DC and any other unstructured aggregators — Em pastes when she's in a session anyway, Claude files via `add_event.py`.
