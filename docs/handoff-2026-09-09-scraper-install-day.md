# Handoff — Scraper install day + first-live-run results

*Written 2026-09-09 by Claude. Branch: main. Follows `handoff-2026-09-08-evening-cleanup.md` which set up the claude.ai prompt batch this session finished executing.*

Em worked through the pending claude.ai prompt round today and pasted results back one by one. Every scraper on the "prompt ready" list from yesterday's handoff is now installed.

---

## What shipped this session

Commits, oldest first:

| SHA | Change |
|---|---|
| `ef28a1b` | Split `docs/scraper-prompt-responses` extensionless file into a proper directory with 5 `.md` files, one per scraper; install National Zoo scraper from the separately-delivered `national_zoo.py` |
| `b060607` | Install Puppet Co Tiny Tots parser (per-artist ShoWare page cascade, hand-mapped `ARTIST_EVT_IDS`) |
| `00761a3` | File the Puppet Co `ARTIST_EVT_IDS` maintenance liability ruling in `docs/decisions.md` |
| `d2255c1` | Install National Children's Museum parser (Next.js + Sanity; 4-strategy cascade, will likely need devtools follow-up) |
| `1ea183e` | Install nbm, pike-and-rose, montgomery-parks parsers (extracted from response `.md` files) |
| `15dd041` | Retire KidFriendly DC — site has no structured events; content is prose inside WP blog posts. Newsletter copy-paste flow replaces it. |
| `d112840` | Doc-drift sweep on `README.md` + `docs/sources.md` (both were still describing the pre-9-08 world) |
| *(this handoff's commit)* | Prune stale sources from health map + fix `_load_prev_health` to prune retired IDs on future runs |

---

## First live CI run — 2026-09-09 15:52 UTC — GREEN

Manual workflow trigger via GitHub Actions after all the day's commits landed. Completed in 73 seconds. `data/events.json` rewritten with 247 events.

### Per-source health from that run

| Source | Count | Read |
|---|---|---|
| smithsonian-events | 533 | ✅ iCal working (feed volume up ~4x since last count — busy fall) |
| mcpl-kids | 110 | ✅ iCal working |
| pike-and-rose | 26 | ✅ new scraper, works first try |
| montgomery-parks | 25 | ✅ new scraper, works first try — Featured Events carousel only (main "All Events" list still JS-populated) |
| rockville-city | 24 | ✅ existing scraper still working |
| seasonal | 12 | ✅ |
| puppetco-tinytots | 8 | ✅ new scraper, works first try — all 5 hand-mapped ARTIST_EVT_IDS resolved correctly |
| butlers-orchard | **0** | 🟡 clean run, no exceptions, zero events. Possibly off-season (Sunflower ended August, Pumpkin Festival starts late September). **See "Manual verification needed" below.** |
| national-building-museum | **0** | 🟡 clean run, zero events. First live run of the delivered parser. **Needs manual verification.** |
| national-childrens-museum | **0** | 🟡 clean run, zero events. **Expected** per the claude.ai response — the calendar is JS-driven; the 4-strategy cascade explicitly warned first live run might come back empty. **Needs manual verification** and, if still zero, devtools Network capture to find the real calendar XHR endpoint (noted in `docs/scraper-prompt-responses/national-childrens-museum.md`). |
| national-zoo | **0** | 🟡 clean run, zero events. First live run. Recon said listing page carries only "a handful of featured upcoming events" — could be genuinely empty right now. **Needs manual verification.** |

Post-CI dedupe: 247 events kept from ~880 raw. Smithsonian's 533 alone gets filtered heavily by age + DMV-location.

---

## Manual verification needed (Em's task)

The four zero-count scrapers above ran cleanly (no exceptions) but returned no events. That could mean:
- The source genuinely has no events in our lookahead window right now (fine, do nothing), OR
- The scraper parses cleanly but doesn't find the right nodes on the real page (bug, needs fix).

**Em needs to eyeball each of these sites manually to confirm which case it is:**

- **butlers-orchard** — https://www.butlersorchard.com/festivals/ — is Pumpkin Festival dated yet? If yes and it's not in `events.json`, scraper is broken.
- **national-building-museum** — https://www.nbm.org/programs-events/ — are there upcoming programs listed on the page? If yes, scraper is broken.
- **national-childrens-museum** — https://nationalchildrensmuseum.org/explore/events — are events visible in the browser? If yes, next move is a devtools Network tab capture of what the calendar widget calls when you click a date (that's the real XHR endpoint we couldn't reach from the server-rendered HTML).
- **national-zoo** — https://nationalzoo.si.edu/visit/events — any upcoming dated events (not the "Today at the Zoo" recurring programs)? Boo at the Zoo should be showing up soon.

If any of these turn out to be scraper bugs, we have the source `.md` files for each in `docs/scraper-prompt-responses/` — the response author explicitly offered to iterate on their scraper if given a saved copy of one live event page's HTML.

---

## Retired sources (permanent — do not "fix")

All rulings filed in `docs/decisions.md`:

- **glen-echo-park** — age mismatch (Em ruling, 9-08)
- **bethesda-row** — no real events calendar (Em ruling, 9-08)
- **kennedy-center-millennium** — age mismatch (retired 9-08)
- **mcpl** (old HTML fallback) — superseded by MCPL iCal (retired 9-08)
- **kidfriendly-dc** — site has no structured events; content is prose inside WP blog posts. Em ruling, 9-09. **Replacement path: newsletter copy-paste flow.** Em subscribes to KFD, pastes newsletter content into a session next time she's here, Claude files each event via `scripts/add_event.py`.

Their stale entries have been pruned from `data/events.json`'s health map this commit, and `_load_prev_health()` now prunes retired IDs on every future run so this won't drift again.

---

## Doc-drift discipline note

Em's ruling this session: **when Claude notices doc drift, fix it same-commit — don't just flag it.** Reporting drift and moving on means it gets lost on reload. Applied twice today (KFD row in sources.md, then the full README + sources.md sweep).

---

## Known unknowns / what to check on next wake

- **The four zero-count scrapers above.** Em to eyeball; if any turn out to be bugs, iterate the corresponding parser.
- **KFD newsletter copy-paste flow.** Em is subscribed. First test is whenever she pastes a "Weekend Round-Up" here — Claude extracts events, files via `add_event.py`.
- **Puppet Co `ARTIST_EVT_IDS` map** — if `puppetco-tinytots` count drops (or a new guest artist appears on `/tiny-tots` without their evt id being in the dict), see the ruling in `docs/decisions.md` for maintenance instructions.
- **Home coordinates** still not set as GitHub Secrets `HOME_LAT` / `HOME_LNG` — distance banding is still `unknown` until Em provides.
