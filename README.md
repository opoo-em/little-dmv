# Little DMV

A phone-first dashboard of kid-friendly events across Montgomery County MD and DC. Built for a specific family — filters age and cost to what actually fits.

**Live:** https://opoo-em.github.io/little-dmv/

## Status

**Phase 1 (dashboard + schema): DONE, deployed.**
**Phase 2 (real data sources): NOT STARTED.** Currently serves 13 hand-written dummy events.

## Repo structure

```
├── index.html              — the dashboard (reader of events.json)
├── favicon.svg             — rainbow heart, Lisa Frank vibes
├── data/
│   └── events.json         — source of truth (dummy data for now)
├── docs/
│   ├── decisions.md        — settled design decisions + WHY (read before proposing changes)
│   └── sources.md          — Phase 2 attack plan: source inventory + priorities
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

## Phase 2 roadmap

Rough order of attack (from `docs/sources.md`):

1. **iCal-having sources first** (fast wins, ~5 min each). Prime candidates: MCPL, Montgomery Parks, Kennedy Center, Smithsonian.
2. **HTML scrapers for high-volume sources** (~30-60 min each). Butler's Orchard, Glen Echo, National Building Museum, KidFriendly DC.
3. **Newsletter / manual for the long tail.** Congressional Plaza signage, farmers market seasonal quirks.

Also pending in Phase 2:
- Home coordinates stored as GitHub Secret
- Scheduled weekly refresh (GitHub Actions, likely Sunday morning)
- On-demand refresh via Claude Code ("refresh little dmv")
- Manual add flow — how Em relays "I saw a sign for X"
