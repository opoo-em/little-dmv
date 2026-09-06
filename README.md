# Little DMV

A phone-first dashboard of kid-friendly events across Montgomery County MD and DC. Built for a specific family — filters age and cost to what actually fits.

## Architecture

Two-layer, source-of-truth separation:

- **`data/events.json`** — canonical event data. Edited by Claude on refresh (weekly cadence or on-demand). Any surface that displays events reads from this file.
- **`index.html`** — the dashboard. A reader of `events.json`. Fetches at page load, renders the filtered list.

Future surfaces (digest email, gcal push, printed weekly sheet, etc.) would be additional readers of the same JSON.

## Hosting

Served as a static site via GitHub Pages. The published URL is bookmarked on the family's phones. No backend, no auth, no runtime dependencies beyond Google Fonts.

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

## Filter rules (baked in)

Events are only added to `events.json` if they pass:

- **Age:** must include ~1-3yr (toddler). Excludes hard-only-babies (e.g. "hatchlings 4mo") and hard-only-older (5+, kindergarten+, elementary).
- **Cost:** no ceiling. All costs included; users toggle free/paid in the UI.

## UI filters (user-controlled)

- Date range: Today / Tomorrow / This Weekend / Next 7 Days / Next 14 Days / Custom
- Place: All / Indoor / Outdoor
- Cost: All / Free / Paid

## Distance calculation

Distance is banded (0-5 / 6-10 / 11-15 / 16-20 / 20+ miles), never precise, to preserve privacy in the public repo. Reference coordinates for distance calculation are stored as a GitHub Secret, never in the repo. The scraper computes the band and only the band is written to `events.json`.

## Roadmap

- [x] Dashboard v1 with dummy events
- [ ] Real event scrapers (MCPL, Butler's Orchard, Kennedy Center, Glen Echo, etc.)
- [ ] Home coordinates stored as GitHub Secret
- [ ] Scheduled weekly refresh (GitHub Actions)
- [ ] On-demand refresh via Claude Code
- [ ] Manual add flow ("I saw a sign for the Congressional Plaza fall festival — add it")
