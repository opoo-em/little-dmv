# Source inventory

Live sources are wired in `scripts/sources.yaml` and pull on the Sunday 12:00 UTC cadence (plus manual triggers). This doc is the human-readable index of what's wired, what's skipped, and what's still on the wishlist.

## Attack order (recommended)

1. **iCal-available sources first** — biggest return per hour. Subscribe, done, zero maintenance.
2. **HTML scrapers for the high-volume sources that lack iCal** — the seven currently wired (see below) cover most of the Phase-2 shortlist.
3. **Newsletter forward / manual relay for the long tail** — aggregators like KidFriendly DC, one-off signage (Congressional Plaza), farmers-market seasonal quirks. Em copy-pastes when she's here anyway; Claude files via `scripts/add_event.py`.

## Status legend

- `?` — feed type unknown, needs investigation
- `iCal` — has iCal, subscribed directly
- `scrape` — per-site HTML scraper wired
- `newsletter` — no feed; Em relays via copy-paste
- `manual` — no discoverable schedule; requires Em to relay
- `skipped` — investigated, deliberately not wired (see `docs/decisions.md`)

---

## Montgomery County (public / government)

| Source | URL | Feed | Priority | Status |
|---|---|---|---|---|
| MCPL — all branches | mcpl.link | iCal | high | wired: `mcpl-kids` (LibNet feed, Toddler + Baby audiences) |
| MoCo Recreation (MoCoRec) | montgomerycountymd.gov/rec | ? | high | not started |
| Montgomery Parks (M-NCPPC) | montgomeryparks.org | scrape | high | wired: `montgomery-parks` (Featured Events carousel only; main list is JS-populated) |
| MCPS family events | mcpsmd.org | ? | low | not started |

**Note on MCPL:** central library system, one LibNet feed covers all branches, pre-filtered to Toddler + Baby audiences.
**Note on Montgomery Parks:** covers Cabin John, Wheaton, Black Hill, Meadowside, Brookside, Locust Grove. Their WordPress install doesn't expose an iCal endpoint despite running The Events Calendar plugin shape — currently we only recover the Featured Events carousel; the "All Events" JS-loaded list is unreached.

## Specific cities / towns

| Source | URL | Feed | Priority | Status |
|---|---|---|---|---|
| City of Rockville | rockvillemd.gov | scrape | med | wired: `rockville-city` (kid-signal filter on) |
| City of Gaithersburg | gaithersburgmd.gov | ? | med | not started |
| City of Takoma Park | takomaparkmd.gov | ? | med | not started |
| Bethesda Urban Partnership | bethesda.org | ? | med | not started |
| Downtown Silver Spring | downtownsilverspring.com | ? | med | not started |
| Germantown (BlackRock Center) | blackrockcenter.org | ? | low | not started |

## Farmers markets (seasonal, weekly)

| Source | URL | Feed | Priority | Status |
|---|---|---|---|---|
| Pike & Rose Farmers Market | pikeandrose.com | scrape | med | wired via `pike-and-rose` scraper (weekday recurrence handled) |
| Rockville Town Square Market | rockvilletownsquare.com | ? | med | not started |
| Bethesda Central Farm Market | centralfarmmarkets.com | ? | med | not started |
| FRESHFARM markets | freshfarm.org | ? | med | not started |
| Silver Spring Farmers Market | fresh-farm.org | ? | low | not started |
| Takoma Park Farmers Market | takomaparkmarket.com | ? | low | not started |

## Shopping / mixed-use centers

| Source | URL | Feed | Priority | Status |
|---|---|---|---|---|
| Pike & Rose | pikeandrose.com | scrape | med | wired: `pike-and-rose` |
| Rockville Town Square | rockvilletownsquare.com | ? | med | not started |
| Congressional Plaza | congressionalplaza.com | manual (likely) | low | not started |
| Bethesda Row | bethesdarow.com | — | **skipped** | No real events calendar; store-promo content only. Em ruled 2026-09-08. Winter Wonderland kept as manual seasonal entry. |
| Rio Washingtonian Center | riowashingtonian.com | ? | low | not started |

## Kid-specific venues (county)

| Source | URL | Feed | Priority | Status |
|---|---|---|---|---|
| Glen Echo Park (main calendar) | glenechopark.org | — | **skipped** | Content is adult-heavy; kid events are 4+. Em ruled 2026-09-08 (`docs/decisions.md`). |
| The Puppet Co — Tiny Tots | thepuppetco.org/tiny-tots | scrape | high | wired: `puppetco-tinytots` (hardcoded ARTIST_EVT_IDS map; see `docs/decisions.md` for maintenance) |
| Wheaton Regional Park (train, carousel) | montgomeryparks.org/wheaton | via Montgomery Parks | high | rolled up under `montgomery-parks` scraper |
| Cabin John Regional Park (train) | montgomeryparks.org/cabinjohn | via Montgomery Parks | high | rolled up under `montgomery-parks` scraper |
| Brookside Gardens | montgomeryparks.org/brookside | via Montgomery Parks | high | rolled up under `montgomery-parks` scraper |
| Meadowside Nature Center | montgomeryparks.org/meadowside | via Montgomery Parks | med | rolled up under `montgomery-parks` scraper |
| Locust Grove Nature Center | montgomeryparks.org/locustgrove | via Montgomery Parks | med | rolled up under `montgomery-parks` scraper |
| Black Hill Regional Park | montgomeryparks.org/blackhill | via Montgomery Parks | med | rolled up under `montgomery-parks` scraper |
| Butler's Orchard (Germantown) | butlersorchard.com | scrape | high | wired: `butlers-orchard` (parses per-festival pages; see `docs/decisions.md`) |

## DC institutions (20-40 min drive)

| Source | URL | Feed | Priority | Status |
|---|---|---|---|---|
| Smithsonian museums | si.edu | iCal | high | wired: `smithsonian-events` (Trumba feed; kid-signal + DMV-location filters on) |
| Smithsonian National Zoo | nationalzoo.si.edu | scrape | high | wired: `national-zoo` (not in the main Smithsonian iCal; dedicated per-site parser) |
| National Building Museum | nbm.org | scrape | high | wired: `national-building-museum` |
| National Children's Museum | nationalchildrensmuseum.org | scrape | high | wired: `national-childrens-museum` (Next.js site — see notes below; first live run may return 0 events) |
| Kennedy Center Millennium Stage | kennedy-center.org/millennium | — | **skipped** | Age mismatch; Felix is still too young for the mostly-adult programming. Retired 2026-09-08. Revisit when he's ~3+. |
| National Gallery of Art | nga.gov | ? | med | not started |
| Hillwood Estate | hillwoodmuseum.org | ? | low | not started |
| Anacostia Community Museum | anacostia.si.edu | ? | low | not started |

## Seasonal / annual events (put on calendar so Em doesn't miss them)

Not really "sources" — one-off events with predictable annual timing. Manually added each year in `data/seasonal.json`.

- Cherry Blossom Festival (late March-early April)
- Butler's Orchard strawberry season (May-June)
- 4th of July fireworks / DC events
- Butler's Orchard pumpkin patch (Sept-Oct)
- Halloween events county-wide (October)
- Zoo Boo (October)
- Zoo Lights (November-January)
- Downtown Rockville Hometown Holidays
- Bethesda Row Winter Wonderland

## Parent-aggregator sites (partial aggregation exists)

| Source | URL | Feed | Priority | Status |
|---|---|---|---|---|
| KidFriendly DC | kidfriendlydc.com | newsletter | high | **skipped as scraper** — no events listing on the site; content is prose inside WP blog posts. Em ruled 2026-09-09 (`docs/decisions.md`). Newsletter copy-paste flow: Em pastes into chat, `add_event.py` files them. |
| Washington Parent Magazine | washingtonparent.com | ? | med | not started |
| Washington Family Magazine | washingtonfamily.com | ? | med | not started |
| DC Urban Moms & Dads | dcurbanmom.com | manual (forum, no feed) | low | not started |
| Certifikid | certifikid.com | ? (deals-focused) | low | not started |

## Newsletter subscriptions (relay to Claude)

Copy-paste flow: Em subscribes, then when she's in a little-dmv session anyway she pastes newsletter content into chat and Claude files each event via `scripts/add_event.py`.

- MCPL kids' newsletter
- Montgomery Parks newsletter
- Butler's Orchard newsletter
- KidFriendly DC newsletter (primary path for KFD content; the scraper attempt was retired)
- Em's local branch library newsletter

## Faith community

- Em's church kid programming — TBD (Em confirms which congregation)

---

## Investigation notes

*Findings and quirks per source. Update as things change.*

### MCPL (wired)
- Feed: `https://mcpl.libnet.info/feeds?data=<base64-config>` where the config selects audience (`Toddler`, `Baby`), all locations, 30-day window.
- Emits `text/calendar` (`BEGIN:VCALENDAR`). Feed pre-filters age, so downstream `age_passes` is redundant but harmless.
- HTML fallback was retired 2026-09-08 (canonical iCal replaced it).

### Smithsonian (wired)
- Feed: `https://www.trumba.com/calendars/smithsonian-events.ics` — Trumba calendar system, no per-audience filter available.
- `require_kid_signal: true` and `require_dmv_location: true` are both on, because the feed covers dozens of physical museums plus nationwide affiliates. Without `require_dmv_location`, out-of-DMV events looked local (they'd get bucketed to the National Mall fallback).
- Normalize infers `venue_key` from the actual venue string on each event, not a single feed-level default.

### Montgomery Parks (wired, partial)
- No iCal endpoint on their WordPress install despite the site running The Events Calendar plugin shape. The scraper covers the Featured Events carousel (~a handful of upcoming items) only.
- The "All Events" list on `/events/` is populated by JS after a filter interaction; the underlying XHR endpoint could not be identified from server-rendered HTML alone.
- If Felix event count from this source stays low, the next move is opening devtools on the live page and finding the real XHR endpoint the filter widget calls — a JSON API is almost certainly there.

### Kennedy Center (skipped)
- Age mismatch retirement, not a technical one. Millennium Stage programming skews adult-classical. Revisit when Felix is ~3+.

### National Children's Museum (wired, watch first run)
- Next.js + Sanity site. Listing page renders event cards client-side; per-event calendar dates are JS-populated too.
- Scraper layers 4 strategies (JSON-LD → link/sitemap discovery → structural HTML → calendar-table heuristic).
- The `<time>`/calendar-heuristic cascade is the piece most likely to return zero events on first run. If that happens, next move is a devtools Network capture of the real calendar XHR endpoint (see `docs/scraper-prompt-responses/national-childrens-museum.md`).

### Puppet Co Tiny Tots (wired, maintenance-liability filed)
- `/tiny-tots` marketing page has no dates or JSON-LD (Squarespace bio page). Real dates live on `thepuppetco.showare.com/eventperformances.asp?evt=<id>` per-artist pages, which ARE server-rendered.
- The scraper hardcodes 5 artists' `evt=` ids because the ShoWare index is JS-rendered and can't be crawled without a browser. New guest artists won't be auto-discovered — see `docs/decisions.md`.

### Butler's Orchard (wired)
- `/events/` calendar widget is client-rendered — the scraper discovers festival nav links from static markup, then parses each festival's own `/festivals/<name>` page for "Dates:" / "Hours:" / "Admission:" blocks. Multi-date lists expand to one event per range.
- Ruling filed in `docs/decisions.md`: do NOT try to scrape the calendar URL directly. Nothing there.

### HTML scrapers wired in `scripts/sources.yaml`

Seven scrapers plus one iCal-preferred HTML fallback module currently enabled:

| Scraper | Module | Notes |
|---|---|---|
| Butler's Orchard | `scripts.scrapers.butlers` | Per-festival page parser (calendar URL is JS-rendered) |
| National Building Museum | `scripts.scrapers.nbm` | Per-site HTML parser |
| National Children's Museum | `scripts.scrapers.national_childrens_museum` | 4-strategy cascade; first live run may need devtools follow-up |
| Smithsonian National Zoo | `scripts.scrapers.national_zoo` | Heading-text matching (site uses 3 different label variants) |
| Pike & Rose | `scripts.scrapers.pike_and_rose` | Listing + per-event detail pages; farmers market recurrence |
| Puppet Co Tiny Tots | `scripts.scrapers.puppetco` | Hardcoded artist→evt map; per-artist ShoWare pages |
| Montgomery Parks | `scripts.scrapers.montgomery_parks` | Featured Events carousel only; main list is JS-populated |
| City of Rockville | `scripts.scrapers.rockville` | HTML fallback with `require_kid_signal: true` |

First real run happens in GitHub Actions (network egress restricted in local Claude Code environment). If any scraper returns zero events on first live run, check the module's own docstring for the fallback strategy — every one of the delivered parsers documents its known failure modes.
