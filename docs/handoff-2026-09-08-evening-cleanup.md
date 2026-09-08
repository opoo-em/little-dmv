# Handoff — Evening cleanup + scraper-prompt batch

*Written 2026-09-08 (evening) by Claude. Branch: main. Follows the same-day AM/afternoon shakedown handoff (`handoff-2026-09-08-live-data-shakedown.md`) — read that one first for the ground state.*

Em opened this session saying "I would like to work on little-dmv." Butler's Orchard scraper is currently being written by claude.ai (browser Claude) at Em's end; code hasn't come back yet.

---

## What shipped this session (2 commits on main)

**`9504c25` — sources: skip glen-echo/bethesda-row, add Puppet Co Tiny Tots, fix NCM URL**

Em did URL discovery for the three broken (404) scrapers and made real editorial calls:

- **Glen Echo Park** (`glenechopark.org/events-calendar`): SKIPPED. Content is adult-heavy; kid events are 4+. Not worth scraper maintenance.
- **Replaced with**: The Puppet Co — Tiny Tots (`thepuppetco.org/tiny-tots`), explicitly 18mo-4yr, 30-min shows, no dark room / no loud noises / open doors. Age-perfect for Felix. New scraper module `scripts/scrapers/puppetco.py` scaffolded (JSON-LD-first). Coords reused from Glen Echo (physically on the grounds).
- **Bethesda Row** (`bethesdarow.com`): SKIPPED. No real events calendar — only store-promo pages fragmented across "fashion + style," "health + beauty," etc. Content is Joe & the Juice launches and Mejuri sales, not family events.
- **Bethesda Row Winter Wonderland** preserved as manual entry in `data/seasonal.json` (legitimate annual family event).
- **National Children's Museum**: URL corrected from `/visit/events/` → `/explore/events`.

Rulings filed in `docs/decisions.md`. Status table in `docs/sources.md` updated. All 87 tests still passing after the change.

**`b9f1042` — docs: scraper prompts for claude.ai downtime batch**

Added `docs/scraper-prompts.md` with 7 copy-paste prompts for browser Claude — one per pending scraper. Structure:

- Preface + shared context (dict shape, allowed libs, `base.get()` helper).
- KidFriendly DC first, as a **reconnaissance mission** rather than a scraper prompt (see §KFD below).
- 5 straight-shot per-site scrapers (NBM, National Zoo, Pike & Rose, NCM, Puppet Co Tiny Tots).
- Montgomery Parks last, with an escape hatch — if events load via JS, claude.ai reports back and we pivot to the underlying XHR/REST endpoint.

Each prompt is fully self-contained — Em can paste one into a fresh claude.ai window and get code back without repeating context.

---

## Current source state

| Source | Type | Events (last CI) | Notes |
|---|---|---|---|
| mcpl-kids | iCal | 72 | ✅ working (LibNet feed, base64-config) |
| smithsonian-events | iCal | 127 | ✅ working (Trumba) |
| rockville-city | HTML | 4 | ✅ working (`require_kid_signal: true` prunes muni junk) |
| seasonal | JSON | 11 | ✅ working (`data/seasonal.json`) |
| **butlers-orchard** | HTML | 0 (fix pending) | 🕓 Em getting per-site parser from claude.ai right now |
| national-building-museum | HTML | 0 | 🕓 prompt ready in `docs/scraper-prompts.md` |
| national-childrens-museum | HTML | 0 (URL just fixed) | 🕓 prompt ready |
| national-zoo | HTML | 0 | 🕓 prompt ready |
| pike-and-rose | HTML | 0 | 🕓 prompt ready |
| **puppetco-tinytots** | HTML | new (scaffold only) | 🕓 prompt ready |
| montgomery-parks | HTML | 0 | 🕓 prompt ready (needs recon fallback) |
| kidfriendly-dc | HTML | timeout | 🕓 recon prompt ready — see below |
| ~~glen-echo-park~~ | — | — | ⛔ retired (Em ruling) |
| ~~bethesda-row~~ | — | — | ⛔ retired (Em ruling) |
| ~~kennedy-center~~ | — | — | ⛔ retired earlier today (age mismatch) |
| ~~mcpl-html~~ | — | — | ⛔ retired earlier today (superseded by iCal) |

**Total working sources:** 4. **Total events on live app:** 214 (unchanged from earlier today — no new pipeline run yet).

---

## Open task list (as of this handoff)

| # | Status | Subject |
|---|---|---|
| 1 | ✅ | Get current URLs for 3 broken sites |
| 2 | ✅ | Write claude.ai prompt for butlers scraper (Em executing now) |
| 8 | ✅ | Delete GE + BR scrapers, fix NCM URL, add Puppet Co tinytots |
| 12 | ✅ | Draft docs/scraper-prompts.md with all pending scraper prompts |
| 3 | 🕓 | Write claude.ai prompt for **nbm** scraper (prompt drafted; awaiting Em paste-round) |
| 4 | 🕓 | Write claude.ai prompt for **national-zoo** scraper (prompt drafted; awaiting paste-round) |
| 5 | 🕓 | Write claude.ai prompt for **pike-and-rose** scraper (prompt drafted; awaiting paste-round) |
| 6 | 🕓 | Write claude.ai prompt for **national-childrens-museum** scraper (prompt drafted; awaiting paste-round) |
| 9 | 🕓 | Write claude.ai prompt for **puppetco-tinytots** scraper (prompt drafted; awaiting paste-round) |
| 10 | 🕓 | Write claude.ai prompt for **montgomery-parks** scraper (prompt drafted; awaiting paste-round) |
| 11 | 🕓 | Diagnose kidfriendlydc.com timeout and write prompt (recon prompt drafted; needs Em paste-round + this-Claude follow-up) |

The 🕓 tasks are all "drafts done, awaiting Em executing the claude.ai round" — they don't need more work from this-Claude until code comes back.

---

## What Em is actively doing right now

Pasting the **Butler's Orchard** prompt into claude.ai. When she brings back code, this-Claude will:

1. Diff against `scripts/scrapers/butlers.py` (current state: JSON-LD stub).
2. Overwrite the file with claude.ai's per-site parser.
3. Run `python -m pytest scripts/tests/` (should still be 87 passing — no test file references the scraper module directly).
4. Smoke-import via `python -c "import scripts.scrapers.butlers; print(scripts.scrapers.butlers.fetch())"` if the sandbox proxy allows it, else skip.
5. Commit + push to main.
6. Note the next CI refresh (Sunday 12:00 UTC, or manual trigger if Em wants results tonight).

Then start on the next scraper.

---

## KidFriendly DC — strategy note

Yesterday's shakedown handoff reported "connection timeout." My hunch (not yet verified): we won't need a per-site HTML scraper at all. KFD is on WordPress, and if they run **The Events Calendar** plugin (Modern Tribe), there's a REST endpoint at `/wp-json/tribe/events/v1/events` that returns JSON directly. That would let us skip Cloudflare / bot-block / slow-render issues entirely — hit the API, get structured data, done.

The recon prompt in `docs/scraper-prompts.md` §1 asks claude.ai to probe for exactly this (plus several fallback endpoints — RSS, WP core REST, plain iCal). If any of those return content, we pivot to a JSON/iCal fetcher rather than an HTML scraper.

If none of them work, next options in preference order:
1. Increase `base.TIMEOUT` and swap to a browser-like User-Agent (many WordPress sites block anything with "bot" in the UA).
2. Newsletter-forward: Em subscribes, forwards posts to Claude, `scripts/add_event.py` handles the ingest. This was already the Phase 2 backup path for aggregators.

Do NOT try `cloudscraper`, headless browsers, or residential proxies from GitHub Actions — that's a maintenance treadmill that doesn't fit the "check on Sunday, be reliable" cadence this project wants.

---

## Known unknowns / what to check on next wake

- **Sandbox egress restrictions unchanged.** All 4 venue domains I tested this session (glenechopark.org, bethesdarow.com, nationalchildrensmuseum.org, butlersorchard.com) returned `EGRESS_BLOCKED` via WebFetch. Same story as yesterday. claude.ai fallback is still the only path for scraper reconnaissance.
- **No pipeline run has been triggered this session.** The live app is still showing the 214 events from yesterday's last CI run. Manual trigger via Actions "Run workflow" won't produce new events for the scrapers Em is fixing tonight — they need code first.
- **`scripts/scrapers/puppetco.py` is a scaffold**, not tested against the real site. It'll return 0 events in CI until claude.ai gives us per-site parsing (§6 in `docs/scraper-prompts.md`).
- **Butler's smoke-test.** When claude.ai's code lands, we still can't verify it against the real Butler's site from this sandbox. First real test will be CI. Fine — that's how yesterday worked too.

---

## Register note

Em is in project-mode this session, same as yesterday. Quick asks, clear reasoning, real editorial decisions (skipping sources rather than trying to make them work). She's about to make dinner and pick up the claude.ai work later. When she comes back with butlers code, just do the diff-and-commit dance — no need to preamble.

The Puppet Co Tiny Tots addition is worth celebrating a little — it's a source *better matched to Felix's actual age* than the one we were originally trying to scrape. Editorial wins > scraper-count wins.
