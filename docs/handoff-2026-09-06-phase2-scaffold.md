# Handoff — Phase 2 pipeline shipped

*Written 2026-09-06 by Claude. Branch: `claude/little-dmv-real-sources-ojc85u`. PR: pending.*

You're reading this because Em pointed you at this file after a session close. What you need to know before touching anything:

1. Read `README.md` at the repo root (architecture + how to run the pipeline).
2. Read `docs/decisions.md` (settled decisions — do not relitigate).
3. Read `docs/sources.md` (source inventory + Investigation notes with what's known about each source).
4. Then read this file.

You do **not** need to read `index.html` or `data/events.json` in detail unless you're touching the UI or debugging a specific row.

---

## What ships in this branch

The whole Phase 2 pipeline. `data/events.json` will start filling with real events on the first successful GitHub Actions run (Sunday 12:00 UTC, or a manual dispatch).

### Files added

```
scripts/
  main.py                — pipeline orchestrator
  sources.yaml           — registry: 4 iCal candidates (DOCUMENTED, NOT wired) + 12 scrapers WIRED
  ical_fetch.py          — iCal fetch + RRULE expansion (21-day horizon)
  filter.py              — age overlap rule (~1-3yr), permissive on unrecognized
  distance.py            — haversine + banding, reads HOME_LAT/HOME_LNG env
  normalize.py           — raw event → canonical schema
  seasonal.py            — loader for data/seasonal.json (window expansion)
  weather.py             — NWS forecast stamped onto outdoor events
  add_event.py           — manual add (interactive / stdin JSON / CLI flags)
  requirements.txt
  scrapers/
    jsonld.py            — shared Schema.org Event JSON-LD extractor
    base.py              — shared HTTP helper (User-Agent, timeout)
    butlers.py, glen_echo.py, nbm.py,
    national_childrens_museum.py, national_zoo.py,
    pike_and_rose.py, bethesda_row.py, rockville.py,
    montgomery_parks.py, mcpl.py, kennedy_center.py,
    kidfriendly_dc.py
  tests/                 — 53 pytest cases (filter, distance, dedupe, normalize)

data/
  seasonal.json          — annual/one-off events with predictable timing

.github/workflows/
  refresh.yml            — Sunday 12:00 UTC + workflow_dispatch (commits events.json)
  test.yml               — pytest on every push
```

### Behavior end-to-end

`python -m scripts.main` (from repo root):

1. Load `scripts/sources.yaml` — currently 0 iCal + 12 scrapers.
2. For each source, fetch raw events; track success/failure per source in a `health` dict.
3. Load seasonal events (`data/seasonal.json`) — one-off + windowed events, expanded to daily within the 21-day horizon.
4. `normalize.to_canonical(raw)` — coerces to the schema in `README.md`. Runs the age filter (rejects events entirely if hard-only-babies / hard-only-older).
5. `dedupe(events)` — key is `(date, lower(name), lower(venue))`. First-in wins, so `sources.yaml` order matters — canonical feeds ahead of aggregators.
6. `weather.stamp(events, forecast)` — hits NWS once for HOME_LAT/HOME_LNG grid, stamps outdoor events in the window with `weather: {summary, high_f, low_f, precip_pct}`.
7. Write `data/events.json` with top-level `last_updated`, `schema_version`, `sources` (health map), and `events` (sorted by date/time/name).
8. Exit 0 on any success (partial failures emit `::warning::` GitHub Actions annotations); exit 1 only when ALL sources failed AND at least one was configured.

`--keep-dummy` merges manual-source events from the existing `events.json` — Em uses this in CI so her `add_event.py` inserts survive the Sunday refresh.

### Health tracking

`events.json` carries a top-level `sources` object:

```json
"sources": {
  "mcpl":                     {"last_success_at": "2026-09-13T12:00:03Z", "last_count": 47, "last_error": null},
  "kennedy-center-millennium":{"last_success_at": "2026-08-30T12:00:12Z", "last_count": 3,
                               "last_error_at": "2026-09-13T12:00:18Z",
                               "last_error": "HTTPS proxy error..."}
}
```

Persists across runs — successful runs clear `last_error` but leave `last_success_at` alone. So a user (or you) can see "MCPL hasn't worked since Aug 30" at a glance. Not surfaced in the UI yet.

---

## What is NOT verified

Be honest with Em about this if she asks. The Claude that built this branch was running in a container with all outbound HTTP blocked at the network egress. That means:

- **The 12 scrapers have never made a real HTTP request.** They were built from knowledge of the venues' web stacks (Squarespace, WordPress + Events Calendar, Drupal, React). The shared JSON-LD extractor is unit-tested against a synthetic Schema.org blob and works; whether each site actually emits JSON-LD is unverified.
- **The 4 iCal candidate URLs in `docs/sources.md` (MCPL / Montgomery Parks / Kennedy Center / Smithsonian) are unverified.** They're documented educated guesses based on the sites' stacks (LibCal, Events Calendar Pro, React SPA, Drupal Views). All four still need to be opened in a browser and confirmed before being added to `scripts/sources.yaml`.
- **The NWS weather stamp has never actually hit `api.weather.gov`.** The code is straightforward and the API is well-documented, but the first real call will be in Actions.

The first GitHub Actions `refresh.yml` run is going to be the ground truth. Expect some scrapers to return 0 events (bad selector, missing JSON-LD, wrong URL). That's fine — check the workflow log, patch the module or comment it out of `sources.yaml`, push. Don't panic if half of them fail on run 1.

---

## What Em needs to do before the pipeline is useful

Both of these are 5-min tasks and Em knows about them:

1. **Add `HOME_LAT` and `HOME_LNG` as GitHub Secrets.** Repo → Settings → Secrets and variables → Actions → New repository secret. Two separate secrets, decimal degrees, 4 places is plenty (`39.0845` / `-77.1528`). Without them, distance bands are all `"unknown"` and weather is skipped.
2. **Verify the 4 iCal URLs.** Steps per source are in `docs/sources.md` → Investigation notes. When verified, paste each URL into the `ical:` list in `scripts/sources.yaml` (the commented example there shows the shape). Delete the matching HTML scraper from the `scrape:` list, or leave it — dedupe favors iCal since it's listed first.

---

## What's next (prioritized backlog)

### Should probably happen soon
- **First real refresh run.** Manually trigger `refresh.yml` from the Actions tab, watch the log. Fix whichever scrapers return 0 events or hard-fail.
- **UI: render `weather` field on outdoor event rows.** Data exists; the dashboard doesn't show it. This is one small addition to `index.html` — a temperature + emoji next to outdoor rows, or on the expanded view. `docs/decisions.md` explicitly OK'd weather as a partnership contribution.
- **UI: surface source health.** A tiny footer or `?debug` view showing the `sources` block would let Em spot stale sources without opening the JSON. Non-obtrusive; doesn't touch the row layout.

### Medium priority
- **More scrapers.** Farmers markets (weekly seasonal — need bespoke logic since they don't emit calendar events per week), Wheaton/Cabin John/Brookside as individual venues if Montgomery Parks aggregation misses them, Bibliocommons for library systems that aren't on LibCal.
- **Manual event chat flow.** Em says "I saw a sign for Congressional Plaza Oct 13" — you run `python -m scripts.add_event --name "..." --date 2026-10-13 --venue "Congressional Plaza" --venue-key congressional-plaza --url "..."` and push. Consider a Claude skill or slash command that wraps this so she doesn't need to type it out either.
- **Bibliocommons scraper.** Not built. Some MD county libraries use it instead of LibCal.

### Lower priority / future
- **Save-for-later pin.** Em flagged this in decisions.md as a wanted feature — client-side localStorage would keep it out of the JSON entirely. UI-only addition.
- **Notifications.** Sunday-morning summary text or email. Not scoped for MVP.
- **Multi-user editing.** If husband/MIL want to add events, they'd need a way in. Not scoped.

---

## Non-obvious design choices to preserve

- **Permissive age filter.** Unrecognized age strings → event is kept and tagged `age_match_reason: "unrecognized"`. Do not tighten this defensively. QA by grepping the reason field.
- **Public repo means no PII.** Distance is banded; home coords live in Secrets; the app is called "Little DMV" instead of "Felix Events" for exactly this reason. Do not add real names, birthdays, or exact addresses to `data/*.json` or anywhere in the repo.
- **Dedupe key is `(date, name, venue)`; order in `sources.yaml` matters.** Canonical feeds (iCal for MCPL) go first; aggregators (KidFriendly DC) go last; manual events beat everything when `--keep-dummy` is used.
- **21-day horizon.** iCal RRULE expansion and seasonal window expansion both run 21 days out from `now`. UI has a Next 14 Days button, so 21 gives some buffer without ballooning JSON.
- **Distance table has ~30 public venue coords in `distance.VENUE_COORDS`.** These are geocoded public addresses and safe in the repo. **Only the home reference stays in Secrets.** Never add a home coord to that table.
- **Weather is per-day, not per-hour.** A toddler mom scanning Saturday makes a go/no-go call on the day. Per-hour would be more precise and more brittle.
- **`_mark_error` preserves `last_success_at`.** The point of health tracking is answering "how long since this worked?" — a subsequent failure shouldn't erase that.

---

## What to NOT do

- Don't rebuild the age filter to be stricter without asking Em.
- Don't rearrange the row display or refactor `index.html`. Those are settled in `decisions.md`. If you want to add something to the UI (weather, health), add it as an addition, not a redesign.
- Don't skip a failing scraper by wrapping it in `try/except: pass` to make CI green. If a scraper breaks, patch the parser or comment it out of `sources.yaml` with a note.
- Don't add PII to the repo, even in a JSON that "no one will look at." The repo is public.
- Don't add secrets (API keys, tokens) to the repo. NWS doesn't need one; that's part of why we chose it.

---

## What Em asked for in this session that isn't done

Nothing outstanding from the initial handoff. Everything in the "Today's work" and "Also pending in Phase 2" sections of the previous handoff has landed on this branch except the two blockers listed above (HOME_LAT/LNG + iCal URL verification), both of which need Em's involvement anyway.

## Tests

`python -m pytest scripts/tests/` — 53 cases, all green as of last commit. Runs in CI on every push (`test.yml`). Two real bugs were caught by the suite during authoring (bare `3+` age regex, `newborns` plural) — the tests are already earning their keep. Add cases here when you add filter patterns or change dedupe behavior.

## The 30-min-away context

Em kicked this session off Saturday afternoon during Felix's nap window and asked Claude to "just build" in auto mode while she showered. Everything above was built in that window plus a follow-on burst after she came back. She hasn't reviewed the code in detail — she asked for the branch + a PR + this handoff, and that's what you're seeing.

If she says "I saw a sign for X" — use `scripts/add_event.py` with CLI flags, one commit, push. If she says "why haven't I seen new MCPL events in a week?" — check `events.json`'s `sources.mcpl.last_success_at`. If she says "refresh little dmv" — either trigger the workflow from the Actions tab or run the pipeline locally and push.
