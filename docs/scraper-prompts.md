# Scraper prompts for claude.ai

Copy-paste prompts to hand to browser Claude (claude.ai) when this-Claude can't reach a venue site directly through the container proxy. Each prompt is self-contained — paste the whole block into a fresh claude.ai conversation, get code back, paste it back into this chat.

**Order of business (recommended):**

1. Reconnaissance for KidFriendly DC first — that's an infra problem (timeout), not just a scraping shape. Findings decide the plan.
2. The five straight-shot scrapers can be done in any order.
3. Montgomery Parks last — the pipeline already tolerates it returning zero events, and it may need iCal negotiation with the site owner rather than more scraping tricks.

**Workflow per scraper:**

1. Open a fresh claude.ai conversation (fresh so context doesn't bleed between venues).
2. Paste the fenced prompt for one scraper.
3. Copy the Python file claude.ai hands back.
4. Paste into our chat with the venue name so this-Claude commits it to the right file and pushes.

---

## Shared context (for reference — DON'T need to paste this separately, it's already in each prompt)

Every scraper module in this project exposes exactly this interface:

```python
ID = "<slug>"
NAME = "<Human Readable>"
URL = "<canonical events page URL>"

def fetch() -> list[dict]:
    ...
```

Helpers already available via `from . import base`:

- `base.get(url) -> str` — GETs with `User-Agent: little-dmv-bot/1.0 (+https://github.com/opoo-em/little-dmv)` and 30-second timeout, calls `raise_for_status()`, returns response text.
- `base.USER_AGENT` and `base.TIMEOUT` constants for direct use if you need to override.

Allowed libraries: `requests`, `beautifulsoup4` (as `from bs4 import BeautifulSoup`), `python-dateutil` (`from dateutil import parser as date_parser`), `icalendar`, Python stdlib. No new deps.

Raw event dict shape (returned by `fetch()`):

```python
{
    "name": str,                  # event title (required, non-empty)
    "start": datetime,            # timezone-aware or naive; pipeline converts to Eastern
    "end": datetime | None,       # None if not on the page
    "venue": str,                 # e.g. "National Building Museum" or a specific room
    "description": str,           # one-paragraph description if available, else ""
    "url": str,                   # link to the individual event page if available, else ""
    "cost_type": "free" | "paid",
    "cost_label": str,            # e.g. "Free", "$10 per child", "Members free / $12 non-members"
    "age": str,                   # human-readable age hint from the page, or "" if unspecified
    "venue_key": str,             # a slug for coordinate lookup — set per scraper (see each below)
    "place": "indoor" | "outdoor",
    "source": str,                # matches ID
}
```

Rules:

- If an event has multiple dates on one listing (e.g. "every Saturday in October"), expand into one dict per date.
- Skip events already past today.
- Don't swallow network errors — `base.get()`'s `raise_for_status()` should bubble up.
- Try Schema.org JSON-LD first if the page has `<script type="application/ld+json">` blobs (our shared `jsonld.py` extractor exists for this — see the Puppet Co example). Fall back to per-site parsing if JSON-LD returns empty or the page doesn't embed it.

---

## 1. KidFriendly DC — RECONNAISSANCE FIRST

**Status:** connection timeout in yesterday's CI. Could be Cloudflare, bot block, geographic block, or a genuinely slow site. We don't know yet.

**Prompt (recon):**

```text
I need reconnaissance on a website that's timing out from our GitHub Actions scraper.

Please WebFetch this URL: https://kidfriendlydc.com/events/

Report back:

1. Did it respond? What status code / how long did it take?
2. Is there a Cloudflare "verify you are human" challenge page, or does the real content load?
3. What CMS is the site running? (WordPress signatures, Squarespace, Ghost, custom — look at meta tags, script src patterns, class names.)
4. If it's WordPress, is there an RSS feed? Try each of these and report which return content:
   - https://kidfriendlydc.com/feed/
   - https://kidfriendlydc.com/events/feed/
   - https://kidfriendlydc.com/events.ics
   - https://kidfriendlydc.com/wp-json/wp/v2/posts?per_page=5
   - https://kidfriendlydc.com/wp-json/tribe/events/v1/events (The Events Calendar plugin API — this is the gold path if it exists)
5. If the events page HTML loads, describe the structure of one event card: what tag/class wraps the event, where the date/time/title/URL/venue live.
6. Any Schema.org JSON-LD Event nodes in the HTML? (Look for `<script type="application/ld+json">` blocks with `"@type": "Event"`.)

Please just report findings — no code yet. I'll decide the scraping approach based on what you find, then send a second prompt.
```

**After you get the recon back, drop it in our chat.** I'll write the follow-up prompt (or, more likely, wire an iCal / REST feed if one exists, no per-site scraper needed).

---

## 2. National Building Museum

**File:** `scripts/scrapers/nbm.py`
**URL:** `https://www.nbm.org/programs-events/`
**Known:** JSON-LD returned 0 events in yesterday's CI. Custom CMS. NBM runs the Building Zone (kid play space) and family-focused programming — most listings are indoor, ages vary widely.

**Prompt:**

```text
I need a Python HTML scraper for the National Building Museum events page: https://www.nbm.org/programs-events/

Please WebFetch that URL and inspect the HTML structure. A previous attempt using Schema.org JSON-LD extraction returned 0 events — so JSON-LD is either absent or malformed. I need per-site HTML parsing.

The scraper is one Python module. It must expose exactly this interface:

    ID = "national-building-museum"
    NAME = "National Building Museum"
    URL = "https://www.nbm.org/programs-events/"

    def fetch() -> list[dict]:
        ...

Use these existing helpers (already imported as `from . import base`):
- base.get(url) -> str — GETs with User-Agent: little-dmv-bot/1.0 (+https://github.com/opoo-em/little-dmv) and 30s timeout, calls raise_for_status(), returns response text.
- base.USER_AGENT and base.TIMEOUT constants also available.

Parse with BeautifulSoup(html, "html.parser") and dateutil.parser (both already in requirements).

Each event dict returned by fetch() must have this shape:

    {
        "name": str,                  # event title (required)
        "start": datetime,            # timezone-aware or naive; downstream converts to Eastern
        "end": datetime | None,       # None if not on the page
        "venue": str,                 # e.g. "National Building Museum" or specific room/exhibit
        "description": str,           # one-paragraph description if available, else ""
        "url": str,                   # link to the individual event page if available, else ""
        "cost_type": "free" | "paid",
        "cost_label": str,            # e.g. "Free", "Members free / $12 non-members"
        "age": str,                   # human-readable age hint from the page, or "" if unspecified
        "venue_key": "national-building-museum",
        "place": "indoor",
        "source": "national-building-museum",
    }

Notes:
- Default place: indoor.
- Many NBM events are member/non-member priced — capture the range in cost_label if visible.
- If an event has multiple date instances (e.g. "every Saturday"), expand into one dict per date.
- Skip events already past today.
- Don't import new third-party libraries beyond requests, beautifulsoup4, python-dateutil, icalendar, stdlib.
- Don't change the module contract or exports.

Return the complete Python file. I'll paste it verbatim into scripts/scrapers/nbm.py.
```

---

## 3. Smithsonian National Zoo

**File:** `scripts/scrapers/national_zoo.py`
**URL:** `https://nationalzoo.si.edu/events`
**Known:** JSON-LD returned 0. The zoo is a Smithsonian unit, but its events don't come through the main Smithsonian Trumba feed we already have wired — needs its own scrape.

**Prompt:**

```text
I need a Python HTML scraper for the Smithsonian National Zoo events page: https://nationalzoo.si.edu/events

Please WebFetch that URL and inspect the HTML structure. A previous attempt using Schema.org JSON-LD extraction returned 0 events. Note: the main Smithsonian iCal feed does NOT include National Zoo events — that's why this needs its own scraper.

The scraper is one Python module. It must expose exactly this interface:

    ID = "national-zoo"
    NAME = "Smithsonian National Zoo"
    URL = "https://nationalzoo.si.edu/events"

    def fetch() -> list[dict]:
        ...

Use these existing helpers (already imported as `from . import base`):
- base.get(url) -> str — GETs with User-Agent: little-dmv-bot/1.0 (+https://github.com/opoo-em/little-dmv) and 30s timeout, calls raise_for_status(), returns response text.

Parse with BeautifulSoup(html, "html.parser") and dateutil.parser (both already in requirements).

Each event dict returned by fetch() must have this shape:

    {
        "name": str,                  # event title (required)
        "start": datetime,            # timezone-aware or naive; downstream converts to Eastern
        "end": datetime | None,
        "venue": str,                 # e.g. "Smithsonian's National Zoo" or a specific area
        "description": str,           # one-paragraph description if available, else ""
        "url": str,                   # link to the individual event page if available, else ""
        "cost_type": "free" | "paid",
        "cost_label": str,
        "age": str,                   # human-readable age hint, or "" if unspecified
        "venue_key": "national-zoo",
        "place": "outdoor",           # zoo default; override to "indoor" per event if page marks otherwise
        "source": "national-zoo",
    }

Notes:
- Default place: outdoor. The zoo grounds are outside; some talks/programs are in buildings — override to "indoor" only if the page explicitly says so.
- Zoo admission is free, but timed-entry passes are required. Individual events may be free or paid on top of that — parse from page.
- Cherry Blossom, ZooLights, and other seasonal programs may have separate ticketing — capture cost_label if visible.
- If an event has multiple date instances, expand into one dict per date.
- Skip events already past today.
- Don't import new third-party libraries beyond requests, beautifulsoup4, python-dateutil, icalendar, stdlib.
- Don't change the module contract or exports.

Return the complete Python file. I'll paste it verbatim into scripts/scrapers/national_zoo.py.
```

---

## 4. Pike & Rose

**File:** `scripts/scrapers/pike_and_rose.py`
**URL:** `https://www.pikeandrose.com/events`
**Known:** JSON-LD returned 0. Mixed-use retail plaza in North Bethesda — live music, seasonal festivals, sometimes kid programming (playground pop-ups, Santa visits). Most events happen outdoors on the plaza.

**Prompt:**

```text
I need a Python HTML scraper for the Pike & Rose events page: https://www.pikeandrose.com/events

Please WebFetch that URL and inspect the HTML structure. A previous attempt using Schema.org JSON-LD extraction returned 0 events. Pike & Rose is a mixed-use retail plaza in North Bethesda, MD — events are live music, seasonal festivals, farmers markets, some kid programming.

The scraper is one Python module. It must expose exactly this interface:

    ID = "pike-and-rose"
    NAME = "Pike & Rose"
    URL = "https://www.pikeandrose.com/events"

    def fetch() -> list[dict]:
        ...

Use these existing helpers (already imported as `from . import base`):
- base.get(url) -> str — GETs with User-Agent: little-dmv-bot/1.0 (+https://github.com/opoo-em/little-dmv) and 30s timeout, calls raise_for_status(), returns response text.

Parse with BeautifulSoup(html, "html.parser") and dateutil.parser (both already in requirements).

Each event dict returned by fetch() must have this shape:

    {
        "name": str,                  # event title (required)
        "start": datetime,
        "end": datetime | None,
        "venue": str,                 # e.g. "Pike & Rose" or a specific space (Grand Park, etc.)
        "description": str,
        "url": str,                   # link to the individual event page if available, else ""
        "cost_type": "free" | "paid",
        "cost_label": str,            # most plaza events are free — default to that if page doesn't say
        "age": str,                   # "" if unspecified — most plaza events are all-ages
        "venue_key": "pike-and-rose",
        "place": "outdoor",           # default; override to "indoor" per event if page marks otherwise
        "source": "pike-and-rose",
    }

Notes:
- Default place: outdoor (plaza).
- Default cost: free / "Free" when the page doesn't say otherwise (most plaza events are free-to-attend).
- Downstream we'll filter out anything that's clearly adult-only (bar tastings, 21+ concerts) using a content filter — don't try to filter those out here, just return what the page shows and mark cost/age accurately.
- If an event has multiple date instances (weekly farmers markets, etc.), expand into one dict per date.
- Skip events already past today.
- Don't import new third-party libraries beyond requests, beautifulsoup4, python-dateutil, icalendar, stdlib.
- Don't change the module contract or exports.

Return the complete Python file. I'll paste it verbatim into scripts/scrapers/pike_and_rose.py.
```

---

## 5. National Children's Museum

**File:** `scripts/scrapers/national_childrens_museum.py`
**URL:** `https://nationalchildrensmuseum.org/explore/events`
**Known:** URL was recently corrected from `/visit/events/`. JSON-LD status unknown at the new URL; likely a Squarespace-ish stack. All events target kids so basically everything passes the age filter.

**Prompt:**

```text
I need a Python HTML scraper for the National Children's Museum events page: https://nationalchildrensmuseum.org/explore/events

Please WebFetch that URL and inspect the HTML structure. First, try to find Schema.org JSON-LD Event nodes (<script type="application/ld+json"> blocks with "@type": "Event"). If those exist and cover the events on the page, use them. If they're absent or incomplete, fall back to per-site HTML parsing.

The scraper is one Python module. It must expose exactly this interface:

    ID = "national-childrens-museum"
    NAME = "National Children's Museum"
    URL = "https://nationalchildrensmuseum.org/explore/events"

    def fetch() -> list[dict]:
        ...

Use these existing helpers (already imported as `from . import base`):
- base.get(url) -> str — GETs with User-Agent: little-dmv-bot/1.0 (+https://github.com/opoo-em/little-dmv) and 30s timeout, calls raise_for_status(), returns response text.

Parse with BeautifulSoup(html, "html.parser") and dateutil.parser (both already in requirements).

Each event dict returned by fetch() must have this shape:

    {
        "name": str,                  # event title (required)
        "start": datetime,
        "end": datetime | None,
        "venue": str,                 # "National Children's Museum" or a specific gallery/space
        "description": str,
        "url": str,                   # link to the individual event page if available, else ""
        "cost_type": "free" | "paid",
        "cost_label": str,            # e.g. "Included with admission", "Members free / $16 non-members"
        "age": str,                   # human-readable age hint from the page, or "" if unspecified
        "venue_key": "national-childrens-museum",
        "place": "indoor",
        "source": "national-childrens-museum",
    }

Notes:
- Default place: indoor (museum).
- Museum admission is paid ($16 non-members, members free). Individual programs are usually included with admission. If the page says otherwise, capture it.
- All programming targets kids — age hints matter here for filtering out infant-only or 5+-only listings. Grab whatever the page says (e.g. "Ages 2-5", "Toddler Time").
- If an event has multiple date instances (weekly storytime, etc.), expand into one dict per date.
- Skip events already past today.
- Don't import new third-party libraries beyond requests, beautifulsoup4, python-dateutil, icalendar, stdlib.
- Don't change the module contract or exports.

Return the complete Python file. I'll paste it verbatim into scripts/scrapers/national_childrens_museum.py.
```

---

## 6. The Puppet Co — Tiny Tots

**File:** `scripts/scrapers/puppetco.py`
**URL:** `https://thepuppetco.org/tiny-tots`
**Known:** Newly-added source. Scaffold committed 2026-09-08 using JSON-LD-first — needs real testing. Tiny Tots is age-explicit: 18mo-4yr, 30-min runtime, no dark room, no loud noises. Every show on the page is age-appropriate by construction.

**Prompt:**

```text
I need a Python HTML scraper for The Puppet Co's Tiny Tots show schedule: https://thepuppetco.org/tiny-tots

Please WebFetch that URL and inspect the HTML structure. First, check for Schema.org JSON-LD Event nodes (<script type="application/ld+json"> blocks). If they exist and cover the schedule, use them. Otherwise fall back to per-site HTML parsing.

The Puppet Co is a small theatre company on the grounds of Glen Echo Park (MD). Tiny Tots is their kid-explicit track — 18 months to 4 years, 30-min runtime, open theatre doors, no dark room, no surprising loud noises. Every show on this page is age-appropriate by construction.

The scraper is one Python module. It must expose exactly this interface:

    ID = "puppetco-tinytots"
    NAME = "The Puppet Co — Tiny Tots"
    URL = "https://thepuppetco.org/tiny-tots"

    def fetch() -> list[dict]:
        ...

Use these existing helpers (already imported as `from . import base`):
- base.get(url) -> str — GETs with User-Agent: little-dmv-bot/1.0 (+https://github.com/opoo-em/little-dmv) and 30s timeout, calls raise_for_status(), returns response text.

Parse with BeautifulSoup(html, "html.parser") and dateutil.parser (both already in requirements).

Each event dict returned by fetch() must have this shape:

    {
        "name": str,                  # show title (required)
        "start": datetime,
        "end": datetime | None,       # add 30 minutes to start if page doesn't say
        "venue": str,                 # "The Puppet Co at Glen Echo Park"
        "description": str,
        "url": str,                   # link to the individual show / ticketing page if available
        "cost_type": "paid",          # Puppet Co shows are ticketed
        "cost_label": str,            # e.g. "$12 per person" if visible, else "See ticketing page"
        "age": "18 months - 4 years", # constant — every Tiny Tots show is this range
        "venue_key": "puppetco-tinytots",
        "place": "indoor",            # theatre
        "source": "puppetco-tinytots",
    }

Notes:
- Every show on the page is a Tiny Tots show — you don't need to filter by kid-appropriateness.
- If the page shows a single title with multiple performance dates (e.g. "The Farmer in the Dell — Saturdays 10am and 11:30am, Oct 3-24"), expand into one dict per date/time.
- Skip performances already past today.
- Puppet Co runs shows in seasonal blocks — the page usually lists the currently-running show plus advance dates.
- Don't import new third-party libraries beyond requests, beautifulsoup4, python-dateutil, icalendar, stdlib.
- Don't change the module contract or exports.

Return the complete Python file. I'll paste it verbatim into scripts/scrapers/puppetco.py.
```

---

## 7. Montgomery Parks

**File:** `scripts/scrapers/montgomery_parks.py`
**URL:** `https://www.montgomeryparks.org/events/`
**Known:** JSON-LD returned 0. Em verified no iCal at `/events/feed/ical/`. WordPress with a custom events plugin (not The Events Calendar). Covers Wheaton, Cabin John, Brookside Gardens, Meadowside, Locust Grove, Black Hill — all high-value kid venues.

**Prompt:**

```text
I need a Python HTML scraper for Montgomery Parks (M-NCPPC) events page: https://www.montgomeryparks.org/events/

Please WebFetch that URL and inspect the HTML structure. Also try these alternate feeds and report if any work:
- https://www.montgomeryparks.org/events/feed/ (verified NOT working)
- https://www.montgomeryparks.org/wp-json/wp/v2/tribe_events?per_page=5
- https://www.montgomeryparks.org/wp-json/tribe/events/v1/events

A previous attempt using Schema.org JSON-LD extraction returned 0 events. Montgomery Parks runs on WordPress but with a custom events implementation, not The Events Calendar plugin. It covers dozens of park sites including Wheaton Regional Park, Cabin John Regional Park, Brookside Gardens, Meadowside Nature Center, Locust Grove Nature Center, Black Hill Regional Park.

The scraper is one Python module. It must expose exactly this interface:

    ID = "montgomery-parks"
    NAME = "Montgomery Parks"
    URL = "https://www.montgomeryparks.org/events/"

    def fetch() -> list[dict]:
        ...

Use these existing helpers (already imported as `from . import base`):
- base.get(url) -> str — GETs with User-Agent: little-dmv-bot/1.0 (+https://github.com/opoo-em/little-dmv) and 30s timeout, calls raise_for_status(), returns response text.

Parse with BeautifulSoup(html, "html.parser") and dateutil.parser (both already in requirements).

Each event dict returned by fetch() must have this shape:

    {
        "name": str,                  # event title (required)
        "start": datetime,
        "end": datetime | None,
        "venue": str,                 # SPECIFIC park name — e.g. "Wheaton Regional Park", "Brookside Gardens". This is important for distance calculation; we key venue coords off these names.
        "description": str,
        "url": str,                   # link to the individual event page if available
        "cost_type": "free" | "paid",
        "cost_label": str,
        "age": str,                   # human-readable age hint from the page, or "" if unspecified
        "venue_key": None,            # leave as None — downstream normalize.infer_venue_key will match on venue string
        "place": "outdoor",           # default; override to "indoor" per event for nature centers, visitor centers
        "source": "montgomery-parks",
    }

Notes on venue:
- The `venue` field is load-bearing here — we need the SPECIFIC park name, not just "Montgomery Parks". Downstream code substring-matches venue strings against a lookup table to get coordinates for distance banding. Recognized park names include: Wheaton Regional Park, Cabin John Regional Park, Brookside Gardens, Meadowside Nature Center, Locust Grove Nature Center, Black Hill Regional Park, Glen Echo Park.
- If the page shows the park name inconsistently (e.g. "Wheaton" alone), still try to expand it to the full name where the source page provides it.

Other notes:
- Default place: outdoor. Nature centers and visitor centers are indoor — mark those.
- If an event has multiple date instances (weekly ranger walks, etc.), expand into one dict per date.
- Skip events already past today.
- Don't import new third-party libraries beyond requests, beautifulsoup4, python-dateutil, icalendar, stdlib.
- Don't change the module contract or exports.

If the events page has a search / filter interface and everything loads via JavaScript, tell me so — we may need to hit the underlying XHR endpoint instead of scraping the rendered HTML.

Return the complete Python file OR a report explaining why scraping isn't viable and what alternative endpoint to hit. I'll paste code verbatim into scripts/scrapers/montgomery_parks.py.
```

---

## When you paste code back

Just say "here's the [venue name] code:" and drop it in — this-Claude will:

1. Diff against the current file for sanity.
2. Overwrite `scripts/scrapers/<name>.py`.
3. Run local tests + smoke import.
4. Commit and push to main.
5. Watch the next CI refresh for how many events it produces.

If claude.ai hands back something that doesn't fit the contract (extra imports, wrong return shape, missing keys), this-Claude will edit it inline rather than bouncing back — the prompts are strict enough that most drift will be small.
