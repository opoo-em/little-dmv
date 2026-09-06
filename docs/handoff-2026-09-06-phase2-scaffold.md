# Handoff — Phase 2 scaffold landed

*Written 2026-09-06 by Claude (Opus 4.7). Branch: `claude/little-dmv-real-sources-ojc85u`.*

## What just shipped

Full Python pipeline scaffold + **12 HTML scrapers** + weekly GitHub Actions cron
+ **seasonal event support** + **pytest suite** + **per-source health tracking** + CLI mode for
manual event add. See the commit history on the branch for the full diff; TL;DR
of new files:

```
scripts/
  main.py               — orchestrator (fetch, normalize, filter, dedupe, write + health)
  sources.yaml          — registry (4 iCal candidates DOCUMENTED but empty; 12 scrapers WIRED)
  ical_fetch.py         — iCal fetch with RRULE expansion, 21-day horizon
  filter.py             — age overlap rule (~1-3yr), permissive on unrecognized
  distance.py           — haversine + banding, reads HOME_LAT/HOME_LNG env
  normalize.py          — raw event → canonical schema
  seasonal.py           — loads data/seasonal.json, expands windows to daily events
  add_event.py          — manual add (interactive / stdin JSON / CLI flags)
  scrapers/
    jsonld.py           — shared Schema.org Event extractor
    butlers.py, glen_echo.py, nbm.py, national_childrens_museum.py,
    national_zoo.py, pike_and_rose.py, bethesda_row.py, rockville.py,
    montgomery_parks.py, mcpl.py, kennedy_center.py, kidfriendly_dc.py
  tests/                — 53 pytest cases (filter, distance, dedupe, normalize)

data/
  events.json           — canonical event data (dashboard reads this)
  seasonal.json         — annual/one-off events (pumpkin patch, Zoo Boo, etc.)

.github/workflows/
  refresh.yml           — Sunday 12:00 UTC + workflow_dispatch (commits events.json)
  test.yml              — pytest on every push
```

## Per-source health tracking

`events.json` carries a top-level `sources` object:

```json
"sources": {
  "mcpl": {
    "last_success_at": "2026-09-06T12:00:03Z",
    "last_count": 47,
    "last_error": null
  },
  "kennedy-center-millennium": {
    "last_success_at": "2026-08-30T12:00:12Z",
    "last_count": 3,
    "last_error_at": "2026-09-06T12:00:18Z",
    "last_error": "HTTPSConnectionPool: max retries exceeded..."
  }
}
```

Persists across runs — successful runs clear `last_error` but leave
`last_success_at` alone, so Em can see "hasn't worked since Aug 30" at a
glance. Not surfaced in the dashboard UI yet — settled row layout doesn't
show it. Future addition: a small footer or `?debug` view.

Tests I ran locally (from container with blocked network):
- Age filter: 10/10 cases pass, including edge cases (K+, months-only, unrecognized).
- End-to-end normalize with synthetic Schema.org JSON-LD: writes a clean event
  dict matching the schema in README.md, including correct distance banding
  when HOME_LAT/HOME_LNG env vars are set.
- Orchestrator with all sources failing (network blocked): correctly exits 1
  and emits `::error::` annotation. Would exit 0 with partial success in CI.

## What still blocks a first real refresh

### 1. GitHub Secrets — home coordinates (BLOCKING for distance banding)
Em: add these under **Settings → Secrets and variables → Actions → New repository secret**:
- `HOME_LAT` — your reference latitude (decimal degrees)
- `HOME_LNG` — your reference longitude (decimal degrees)

Without them, every event will show `distance_mi_range: "unknown"`. Everything
else still works.

### 2. iCal endpoints — need URL verification from a reachable network
The four iCal candidates (MCPL, Montgomery Parks, Kennedy Center, Smithsonian)
are documented in `docs/sources.md` → Investigation notes but the exact URLs
weren't verifiable from this session's network. Next steps for whoever picks
this up:

- Open each candidate URL in a browser and find the actual "Subscribe" / iCal
  link. Copy that URL.
- Add each verified feed to `scripts/sources.yaml` under `ical:` (there's a
  commented block showing the shape).
- If MCPL uses LibCal (mcpl.libcal.com), the iCal URL has an `iCal=1` param.
- If Montgomery Parks' The Events Calendar iCal works, delete the
  `montgomery-parks` entry from the `scrape:` list (or leave it — dedupe favors
  iCal).
- Kennedy Center likely doesn't have a public iCal (React SPA). If not, add a
  scraper wrapping `kennedy_center.py` in the same pattern as `nbm.py`.

## What Em asked for but isn't done

- **Manual add via chat.** Em says "I saw a sign for Congressional Plaza Oct 13"
  and Claude adds it. The mechanism is `scripts/add_event.py --stdin` with a
  JSON blob — but Em hasn't been shown this yet and no formal chat command
  exists. Consider: (a) inline `add_event` call when she says this, then push
  a commit; (b) a slash command in a future skill.

- **On-demand refresh via chat.** Em says "refresh little dmv" and Claude runs
  the pipeline + pushes. Also works via the "Run workflow" button in the
  Actions tab. No shortcut wired yet — just run
  `python -m scripts.main && git add data/events.json && git commit && git push`
  from the little-dmv clone.

## Non-obvious design choices worth remembering

- **Permissive age filter.** Unrecognized age strings → the event is kept and
  tagged `age_match_reason: "unrecognized"`. This is intentional per
  `docs/decisions.md`. QA is by scanning the reason field, not by tightening
  the filter defensively.

- **Dedupe key is (date, name, venue).** Order in `sources.yaml` matters —
  iCal feeds should be listed first, aggregators (KidFriendly DC) last, so the
  canonical version wins when duplicates appear.

- **Distance table is public.** `distance.VENUE_COORDS` has ~30 public venue
  coordinates. This is deliberately safe — venues are geocoded public places.
  Only the home reference stays in Secrets. Never add a home coord to that table.

- **21-day horizon.** iCal RRULE expansion runs 21 days out from `now`. The UI
  has a Next 14 Days button, so 21 gives some buffer without ballooning JSON size.

## What next-Claude should NOT do

- Don't rebuild the age filter to be stricter without asking Em first.
- Don't re-arrange the row display or refactor `index.html` — those are settled.
- Don't add PII to the repo (birthdays, real addresses, Felix's name, husband/MIL
  names). The public-repo constraint is why we have banded distances and why
  the app is called "Little DMV" instead of "Felix Events."
- Don't skip a failing test or wrap a broken scraper in `try/except: pass` to
  make the workflow green. If a scraper breaks, patch the parser or comment
  it out of `sources.yaml` with a note.

## The 30-min-away context

Em spun this Phase 2 work up on Saturday afternoon during Felix's nap window,
in auto mode while showering. She wanted momentum, not check-ins. The scaffold
represents ~1% of her token budget for this session — everything above was
built in the "just go" mode she asked for.

The dashboard already exists and looks lovely with dummy data. The only thing
between "dummy" and "real" now is: HOME_LAT/HOME_LNG in Secrets, iCal URLs
verified, first Actions run pushed. Every one of those is a 5-minute task.
