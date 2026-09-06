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
| Bethesda Row | bethesdarow.com | ? | med | not started |
| Rio Washingtonian Center | riowashingtonian.com | ? | low | not started |

## Kid-specific venues (county)

| Source | URL | Feed | Priority | Status |
|---|---|---|---|---|
| Glen Echo Park (Puppet Co, arts, carousel) | glenechopark.org | ? | high | not started |
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
- (empty — investigate first)

### Montgomery Parks
- (empty — investigate first)

### Kennedy Center
- (empty — investigate first)
