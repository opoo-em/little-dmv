# Source inventory

Ready for Phase 2 (real data). Every entry needs to be classified (feed type), prioritized, and wired.

## Attack order (recommended)

1. **iCal-available sources first** — biggest return per hour. Subscribe, done, zero maintenance.
2. **HTML scrapers for high-volume sources** — Butler's Orchard, Glen Echo, National Building Museum, KidFriendly DC.
3. **Newsletter / manual for the long tail** — Congressional Plaza signage, farmers market seasonal quirks.

## Status legend

- `?` — feed type unknown, needs investigation
- `iCal` — has iCal, subscribe directly
- `scrape` — needs HTML scraper
- `newsletter` — no feed, but has email list
- `manual` — no discoverable schedule; requires Em to relay

---

## Montgomery County (public / government)

| Source | URL | Feed | Priority | Status |
|---|---|---|---|---|
| MCPL — all branches | mcpl.link | ? (likely iCal) | high | not started |
| MoCo Recreation (MoCoRec) | montgomerycountymd.gov/rec | ? | high | not started |
| Montgomery Parks (M-NCPPC) | montgomeryparks.org | ? | high | not started |
| MCPS family events | mcpsmd.org | ? | low | not started |

**Note on MCPL:** central library system, likely one feed covers all branches. Massive event volume. Highest ROI first target.
**Note on Montgomery Parks:** covers Cabin John, Wheaton, Black Hill, Meadowside, Brookside, Locust Grove. Likely centralized.

## Specific cities / towns

| Source | URL | Feed | Priority | Status |
|---|---|---|---|---|
| City of Rockville | rockvillemd.gov | ? | med | not started |
| City of Gaithersburg | gaithersburgmd.gov | ? | med | not started |
| City of Takoma Park | takomaparkmd.gov | ? | med | not started |
| Bethesda Urban Partnership | bethesda.org | ? | med | not started |
| Downtown Silver Spring | downtownsilverspring.com | ? | med | not started |
| Germantown (BlackRock Center) | blackrockcenter.org | ? | low | not started |

## Farmers markets (seasonal, weekly)

| Source | URL | Feed | Priority | Status |
|---|---|---|---|---|
| Pike & Rose Farmers Market | pikeandrose.com | ? | med | not started |
| Rockville Town Square Market | rockvilletownsquare.com | ? | med | not started |
| Bethesda Central Farm Market | centralfarmmarkets.com | ? | med | not started |
| FRESHFARM markets | freshfarm.org | ? | med | not started |
| Silver Spring Farmers Market | fresh-farm.org | ? | low | not started |
| Takoma Park Farmers Market | takomaparkmarket.com | ? | low | not started |

## Shopping / mixed-use centers

| Source | URL | Feed | Priority | Status |
|---|---|---|---|---|
| Pike & Rose | pikeandrose.com | ? | med | not started |
| Rockville Town Square | rockvilletownsquare.com | ? | med | not started |
| Congressional Plaza | congressionalplaza.com | manual (likely) | low | not started |
| Bethesda Row | bethesdarow.com | — | **skipped** | No real events calendar; store-promo content only. Em ruled 2026-09-08. Winter Wonderland kept as manual seasonal entry. |
| Rio Washingtonian Center | riowashingtonian.com | ? | low | not started |

## Kid-specific venues (county)

| Source | URL | Feed | Priority | Status |
|---|---|---|---|---|
| Glen Echo Park (main calendar) | glenechopark.org | — | **skipped** | Content is adult-heavy; kid events are 4+. Em ruled 2026-09-08 (`docs/decisions.md`). |
| The Puppet Co — Tiny Tots | thepuppetco.org/tiny-tots | scrape | high | scaffold committed 2026-09-08; needs per-site parsing if JSON-LD returns empty |
| Wheaton Regional Park (train, carousel) | montgomeryparks.org/wheaton | ? (via Montgomery Parks) | high | not started |
| Cabin John Regional Park (train) | montgomeryparks.org/cabinjohn | ? (via Montgomery Parks) | high | not started |
| Brookside Gardens | montgomeryparks.org/brookside | ? (via Montgomery Parks) | high | not started |
| Meadowside Nature Center | montgomeryparks.org/meadowside | ? (via Montgomery Parks) | med | not started |
| Locust Grove Nature Center | montgomeryparks.org/locustgrove | ? (via Montgomery Parks) | med | not started |
| Black Hill Regional Park | montgomeryparks.org/blackhill | ? (via Montgomery Parks) | med | not started |
| Butler's Orchard (Germantown) | butlersorchard.com | scrape | high | not started |

## DC institutions (20-40 min drive)

| Source | URL | Feed | Priority | Status |
|---|---|---|---|---|
| Smithsonian museums | si.edu | ? (possibly iCal per museum) | high | not started |
| National Building Museum | nbm.org | scrape | high | not started |
| National Children's Museum | nationalchildrensmuseum.org | ? | high | not started |
| Kennedy Center Millennium Stage | kennedy-center.org/millennium | ? (likely iCal) | high | not started |
| National Gallery of Art | nga.gov | ? | med | not started |
| Hillwood Estate | hillwoodmuseum.org | ? | low | not started |
| Anacostia Community Museum | anacostia.si.edu | ? | low | not started |

## Seasonal / annual events (put on calendar so Em doesn't miss them)

Not really "sources" — one-off events with predictable annual timing. Should be manually added each year with a repeating pattern.

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
| KidFriendly DC | kidfriendlydc.com | scrape | high | not started |
| Washington Parent Magazine | washingtonparent.com | ? | med | not started |
| Washington Family Magazine | washingtonfamily.com | ? | med | not started |
| DC Urban Moms & Dads | dcurbanmom.com | manual (forum, no feed) | low | not started |
| Certifikid | certifikid.com | ? (deals-focused) | low | not started |

## Newsletter subscriptions (relay to Claude)

- MCPL kids' newsletter
- Montgomery Parks newsletter
- Butler's Orchard newsletter
- KidFriendly DC newsletter
- Em's local branch library newsletter

## Faith community

- Em's church kid programming — TBD (Em confirms which congregation)

---

## Investigation notes (fill in during Phase 2)

*As we investigate each source, note here what we found: iCal endpoint URL, scraper strategy, quirks, rate limits, robots.txt notes.*

### MCPL
- Public site: mcpl.link → redirects to montgomerycountymd.gov/library
- Event system: MCPL runs their calendar on Springshare LibCal (mcpl.libcal.com pattern is standard for county libraries on this platform).
- **Verify:** open the kids' calendar page, look for a "Subscribe" / iCal button in the top-right of the LibCal widget. LibCal iCal URLs look like `https://mcpl.libcal.com/calendar/kids?cid=<id>&audience=<id>&iCal=1`.
- Likely one feed per audience (kids / teens / adults); we want the kids feed.
- **Status:** URL not yet pasted into `scripts/sources.yaml`. Pipeline scaffold is ready; when the URL is verified, add to the `ical:` list and the next `python -m scripts.main` will start pulling.

### Montgomery Parks
- Public site: montgomeryparks.org — runs on WordPress with The Events Calendar (Modern Tribe) plugin.
- The Events Calendar plugin serves iCal at `/events/feed/ical/` (or from any events archive URL with `?ical=1` appended). Very reliable pattern.
- **Verify:** try `https://www.montgomeryparks.org/events/feed/ical/` and confirm it returns a `text/calendar` body starting with `BEGIN:VCALENDAR`.
- Likely covers Wheaton, Cabin John, Brookside, Meadowside, Locust Grove, Black Hill, Rock Creek — one feed for the whole park system.
- **Note on Glen Echo:** same plugin pattern likely — `glenechopark.org/events/feed/ical/` may exist. If so, move Glen Echo from the HTML scraper into iCal.
- **Status:** URL not yet pasted into `scripts/sources.yaml`.

### Kennedy Center
- Public site: kennedy-center.org, Millennium Stage lives at `/whats-on/millennium-stage/`.
- Kennedy Center's calendar tech has changed over the years; recent site is React-based which usually means the iCal is behind an API endpoint rather than a plain URL.
- **Verify approach:** view the Millennium Stage calendar page, open network tab, look for XHR to `/api/calendar/…` or a "Download to calendar" export button on individual event pages.
- Fallback if no site-wide iCal: scrape the Millennium Stage listing page (Schema.org Event JSON-LD is likely embedded).
- **Status:** URL not yet pasted; may downgrade to scraper if no iCal exists.

### Smithsonian
- Public site: si.edu/events — Drupal-based, with per-museum sub-sites.
- **Verify:** try `https://www.si.edu/events/feed/ical`. Drupal's Views module often serves iCal but the exact URL varies per site.
- Per-museum calendars may be richer (e.g. Natural History has its own event feed).
- **Status:** URL not yet pasted; may need per-museum feeds.

### HTML scrapers wired in `scripts/sources.yaml`
Four scrapers are enabled now and will run on the next pipeline invocation:

| Scraper | Module | Strategy |
|---|---|---|
| Butler's Orchard | `scripts.scrapers.butlers` | JSON-LD from `butlersorchard.com/events/` |
| Glen Echo Park | `scripts.scrapers.glen_echo` | JSON-LD from `glenechopark.org/calendar-of-events` |
| National Building Museum | `scripts.scrapers.nbm` | JSON-LD from `nbm.org/programs-events/` |
| KidFriendly DC | `scripts.scrapers.kidfriendly_dc` | JSON-LD from `kidfriendlydc.com/events/` |

All four use the shared `scrapers/jsonld.py` extractor. First real run will happen in GitHub Actions (network egress is restricted in the local Claude Code environment). If any scraper returns zero events, the site probably doesn't emit Schema.org Event nodes — patch the module with per-site HTML parsing.
