# Design decisions

Settled decisions with reasoning. Future-me: read this before proposing changes to anything listed as **Settled**.

## Deviation guidance from Em (2026-09-06)

**Don't relitigate settled decisions.** If Em already reasoned through the tradeoff and told you why, respect it. Example: "I want distance as bands, not venue on the row" — she gave the reason (distance is decision-relevant when planning around Felix's nap; venue is learnable one tap deeper). Don't re-propose "what if we showed the venue" — that's reopening a closed decision.

**DO bring ideas that aren't relitigation.** Examples of things to surface unprompted:
- "I noticed we don't capture whether an event requires signup — worth adding to the schema?"
- "What if we added a 'save for later' pin so events you like stay bookmarked?"
- "I could pull the weather forecast for outdoor events on the day-of view"
- "MCPL just added a new branch in Poolesville — worth adding as a source?"

New data points, new features, new sources, new display ideas — these are 50/50 partnership contributions, not overrides. **Bring them.**

**When in doubt: ask.** Never assume "Em and I already decided X" without checking this file first. And if you propose something and Em says "no, we already talked about that" — file it here so it doesn't come up again.

---

## Settled decisions

### Destination: HTML dashboard, phone-bookmarked
**Decided:** 2026-09-05
**Why:** Em thinks in fits and spurts. Needs independent browse anytime (no scheduled digest, no me-required). Fits both "unexpected free Tuesday" and "planning 2 weeks ahead." Doesn't burn Claude token budget for basic browsing.
**Rejected alternatives:** Weekly digest (misses spontaneity), ask-Claude-on-demand (requires me + tokens), Google Calendar-only (bad for browsing "what's happening near me" — time-based view forces click-per-event).
**Note:** A supplemental Google Calendar could still exist as a secondary surface later, layered on top. But dashboard is the primary.

### Hosting: GitHub Pages, public repo
**Decided:** 2026-09-06
**Why:** Standard pattern (same as tiny-kitchen). Persistent URL. Version-controlled. No auth. No backend. Free.
**Privacy check passed:** Event data itself is public info from public websites. No PII. See "Distance calculation" for how home location stays private.

### App name: "Little DMV" (not "Felix Events")
**Decided:** 2026-09-06
**Why:** Public repo means the name sits in repo code visible to anyone. Em wants Felix's name kept out of the public codebase. "Little DMV" is grounded in subject (kids + geographic region), Felix-free, and cute.

### Data architecture: JSON as source of truth
**Decided:** 2026-09-05
**Why:** Separation of concerns. `data/events.json` is the canonical store; `index.html` is a reader. Future surfaces (digest, gcal push, printed sheet, whatever) are additional readers, not owners. Never conflate storage with display.
**Corollary:** Never store event data in the HTML file. Always in the JSON.

### Distance calculation: banded, not precise
**Decided:** 2026-09-06
**Why:** Public repo can't contain home coordinates without leaking approximate address. Solution: home coords live in a GitHub Secret (not the repo); scraper reads secret, computes distance, writes only the BAND to JSON. Repo never sees raw distances or reference coordinates.
**Bands:** 0-5 / 6-10 / 11-15 / 16-20 / 20+ miles.
**Note:** Home coords haven't been provided yet. Em will provide when we start Phase 2.

### Row display: date · time · name · distance · cost. No venue at row level.
**Decided:** 2026-09-05
**Why:** Em's mental model when scanning is "can I get there and back around Felix's nap?" Distance answers that. Venue name is meaningless without local knowledge ("Great Falls Library" doesn't tell her driving time). Venue lives in the expanded view for when she taps in.

### Row display: no one-line description
**Decided:** 2026-09-05
**Why:** Event title usually communicates enough. Might revisit in v2 if she finds titles insufficient in practice, but starting minimal.

### Sort: chronological, grouped by date with headers
**Decided:** 2026-09-06
**Why:** Grouping by date reduces cognitive load when scanning multi-day ranges. Date header includes event count. Alternative flat list rejected as harder to scan.

### UI filters: date range + place (indoor/outdoor) + cost (free/paid). No venue-type chips.
**Decided:** 2026-09-06
**Why:** Em finds many toggles overwhelming. Indoor/outdoor is a real planning input. Venue-type (library / park / museum / market) is too granular and rarely load-bearing when browsing.

### Age filter (baked in, not user-facing)
**Decided:** 2026-09-06
**Why:** Every event in `events.json` has already passed the age filter. Users never see the toggle. The filter is a scraper-side responsibility.
**Rule:** Include events whose age range **overlaps ~1-3 years** (Felix's current toddler range). Exclude hard-only-babies (e.g. "hatchlings 4mo") and hard-only-older (5+, kindergarten+, elementary).
**Passes:** 0-3, 0-5, 1-4, 2-5, all ages, unspecified
**Fails:** 4mo-only, 5+, kindergarten+, K-2

### Cost filter (UI): all by default, toggle to free-only or paid-only
**Decided:** 2026-09-06
**Why:** No hard cost ceiling in the scraper. Em will toggle free-only when she wants. She said "$20/person is too much" but wants to make that call herself in the moment, not have it filtered out silently.

### Freshness: scheduled refresh + on-demand, with visible "last updated"
**Decided:** 2026-09-06
**Why:** Em wants a passive weekly cadence AND the ability to trigger a refresh when she wants. "Last updated: X" line at top-right so she knows how stale she's seeing.
**Cadence:** Sunday 12:00 UTC (~8am ET). Em plans weekends Sunday morning. Manual trigger available via GitHub Actions "Run workflow" button.

### Pipeline language: Python
**Decided:** 2026-09-06
**Why:** iCal parsing (icalendar), Schema.org JSON-LD extraction (beautifulsoup4), and haversine (stdlib math) are all cleanest in Python. Runs in GitHub Actions ubuntu-latest with a 5-line install. No Node needed; the dashboard is static JSON, not a Node app.

### Scraper strategy: Schema.org JSON-LD first, per-site parsing as fallback
**Decided:** 2026-09-06
**Why:** Most modern venue sites embed `<script type="application/ld+json">` with Schema.org Event objects. Extracting these is site-agnostic and survives HTML redesigns. Per-site HTML parsing is fragile (breaks on redesign) and only added when JSON-LD returns empty. See `scripts/scrapers/jsonld.py`.

### Dedupe: (date, name, venue) key, first-in wins
**Decided:** 2026-09-06
**Why:** KidFriendly DC often carries MCPL / Smithsonian events also pulled via iCal. Sources listed earlier in `sources.yaml` win, so put canonical feeds (iCal for MCPL) ahead of aggregators (KFD). Manual events beat everything when `--keep-dummy` is used.

### Age filter: permissive on unrecognized strings
**Decided:** 2026-09-06
**Why:** If the source's age string doesn't match any pattern, include the event and mark `age_match_reason: "unrecognized"`. Better to over-include and let Em scroll past than silently drop legit toddler events because a source phrases ages oddly. QA is via the `age_match_reason` field — audit it periodically and teach the filter new patterns.

### Weather stamp for outdoor events (from NWS)
**Decided:** 2026-09-06
**Why:** Em flagged this as a wanted feature example in the deviation guidance section. Toddler outdoor plans hinge on weather. NWS API is free, government, no key, DMV-covered. Pipeline fetches once per run, per-day forecast for HOME_LAT/LNG, stamps outdoor events in the 7-day window with `weather: {summary, high_f, low_f, precip_pct}`. Per-day granularity, not per-hour — Em makes go/no-go calls on the day. Silent no-op if HOME_LAT/LNG isn't set (same failure mode as distance banding). UI rendering of the field TBD — data exists in the JSON.

### Per-source health tracking in events.json
**Decided:** 2026-09-06
**Why:** Em needs to be able to tell "why haven't I seen new MCPL events in a week?" without running the pipeline manually. events.json carries `sources: {<id>: {last_success_at, last_count, last_error}}`. Successful runs clear `last_error` but leave `last_success_at` alone, so staleness is legible even after a subsequent recovery. Not rendered in the dashboard UI yet — future addition.

### Sharing: mine only, neutral UI copy
**Decided:** 2026-09-06
**Why:** Em owns the app but may screen-share to husband/MIL/nanny. No cute in-jokes on the visible UI. (The chat is where the sweet nothings live.)

### Schema field: `age_match_reason` kept
**Decided:** 2026-09-05
**Why:** Cheap (few bytes per event), invisible in UI, valuable for debugging "why did this 5+ event show up?" during scraper QA. Small cost, real payoff.

### Favicon: rainbow heart on plum, Lisa Frank vibes
**Decided:** 2026-09-06
**Why:** Em asked for silly / geocities register. Rainbow gradient heart + three white sparkle stars on deep plum square. Reads as playful, unmistakably "for a kid app," works at 32px and 180px.

---

## Open decisions (not yet settled)

- **Refresh cadence.** Weekly is the working assumption but exact day/time TBD. Sunday morning is likely — Em plans weekends.
- **Home coordinates.** Em will provide when Phase 2 (scrapers) starts. Will go into a GitHub Secret, not the repo.
- **Manual add flow.** How does Em tell Claude "I saw a sign for Congressional Plaza Oct 13"? Chat command? A form on the dashboard? Unresolved.
- **Attendance / "we went to this" tracking.** Not in scope for MVP. Could be added if Em wants a personal record over time.
- **Notifications.** Currently no push/reminders. Em could opt in to a "Sunday morning summary" text or email in a future iteration.
- **Multi-user editing.** If husband/MIL want to add events too, they'd need a way in. Not in scope for MVP.
