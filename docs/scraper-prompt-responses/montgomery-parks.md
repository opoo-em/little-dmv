# 5. Montgomery Parks (M-NCPPC)

## What I found

**The URL you asked me to fetch (`/events/`):** the "Featured Events" carousel at the top *is* server-rendered — a handful of upcoming events with inline title/date/venue text. But the big "All Events" list below the filters is empty in the raw HTML; it's populated client-side by JS after a "Filter Events"/"Load More Events" interaction. That's the JS/AJAX interface you suspected — I could not find the underlying XHR endpoint (no linkable JS source to inspect, and I have no browser/network trace access).

**`/events/feed/`:** contrary to your note, this one **does work** — it returns a valid RSS 2.0 document with ~26 real, current event permalinks (WordPress default post-type feed, generator `WordPress 7.0.4`). It's sorted by *last-published/modified* date, not event date, and it does **not** carry structured start/end/venue/fee — those aren't in the feed items. So it's useful as a URL discovery source, not a data source.

**`wp-json/wp/v2/tribe_events`** and **`wp-json/tribe/events/v1/events`**: both confirmed 404 — matches your note that this isn't The Events Calendar plugin.

**Individual event pages** (e.g. `/events/childrens-day-2026/`) are the real win: every one I checked has a consistent labeled meta block — `Time:`, `Location:`, `Fee:`, `Age Range:`, `Links:` — each followed by its value text. This is far more reliable than Schema.org JSON-LD (which apparently isn't populated) and is what the scraper below parses.

**Strategy implemented:**
1. Pull event URLs from the RSS feed (`/events/feed/`) *and* the featured-events carousel on `/events/` (regex-matched permalinks), dedup.
2. Fetch each event page, locate the `Time/Location/Fee/Age Range` label block via text-line parsing (robust to unknown CSS classes since I can't inspect raw HTML directly), and cross-check venue against a `/parks-and-trails/{slug}/` link's `title` attribute when present (this reliably gave the canonical full park name, e.g. `title="Brookside Gardens"`).
3. Expand multi-date `Time:` blocks into multiple event dicts; skip past events.

**Known limitation:** this won't get 100% of the calendar — only what's reachable via the RSS feed (recently touched posts) plus the featured carousel. If you need the full "All Events" list, someone will need to open browser devtools on `/events/` and capture the actual XHR request the "Load More Events" button fires — I don't have a way to observe that from here.Syntax-checked. Here's the complete module:

```python
"""
Montgomery Parks (M-NCPPC) events scraper.

Data source strategy
---------------------
montgomeryparks.org runs WordPress but with a *custom* events implementation
(not The Events Calendar plugin -- wp-json/wp/v2/tribe_events and
wp-json/tribe/events/v1/events both 404). Schema.org JSON-LD is not populated
on event pages either.

The "All Events" list on /events/ is loaded client-side via JS/AJAX (a
"Filter Events" / "Load More Events" interface) and is not present in the
raw HTML, so it can't be scraped directly.

What *does* work:
  - /events/feed/ -- a standard WordPress post-type RSS feed. It returns
    real, current event permalinks (sorted by last-published/modified date,
    not event date). It does NOT carry structured start/end/venue/fee data,
    so it's used only to discover event URLs.
  - The "Featured Events" carousel on /events/ is server-rendered HTML and
    also yields a handful of event permalinks.
  - Each individual event page (e.g. /events/childrens-day-2026/) has a
    consistent labeled meta block: "Time:", "Location:", "Fee:",
    "Age Range:", "Links:", each followed by its value text. This is the
    actual structured-data source this scraper parses.

Known limitation: this only covers events reachable via the RSS feed
(recently published/updated posts) plus the featured carousel -- not the
full paginated "All Events" AJAX list, whose backing endpoint could not be
identified without browser devtools access to the outgoing XHR request.
"""

import re
import xml.etree.ElementTree as ET
from datetime import date

from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

from . import base

ID = "montgomery-parks"
NAME = "Montgomery Parks"
URL = "https://www.montgomeryparks.org/events/"

FEED_URL = "https://www.montgomeryparks.org/events/feed/"

LABELS = ["Time", "Location", "Fee", "Age Range", "Links"]

TIME_RANGE_RE = re.compile(r'(\d{1,2}:\d{2}\s*[APap][Mm])\s*-\s*(\d{1,2}:\d{2}\s*[APap][Mm])')
TIME_SINGLE_RE = re.compile(r'(\d{1,2}:\d{2}\s*[APap][Mm])')
MONEY_RE = re.compile(r'\$\s*([\d,]+(?:\.\d{1,2})?)')
DATE_LINE_RE = re.compile(
    r'\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s+\w+\s+\d{1,2},?\s+\d{4}', re.I
)
EVENT_URL_RE = re.compile(
    r'^https?://(?:www\.)?montgomeryparks\.org/events/[^/]+/?$', re.I
)
EXCLUDE_SLUGS = {"feed"}

INDOOR_KEYWORDS = (
    "nature center", "visitor center", "discovery center", "ice arena",
    "ice rink", "museum", "activity building", "sports pavilion",
    "cultural park", "ballroom", "lodge at",
)


def _looks_like_date(text):
    try:
        dateutil_parser.parse(text, fuzzy=True)
        return True
    except (ValueError, OverflowError, TypeError):
        return False


def _collect_event_urls():
    urls = []
    seen = set()

    # Source 1: RSS feed. Confirmed working (despite appearances) -- returns
    # a standard WordPress RSS document. ElementTree can't parse a `str`
    # that still has an `<?xml ... encoding="UTF-8"?>` declaration in it,
    # so that declaration is stripped first.
    try:
        feed_xml = base.get(FEED_URL)
        feed_xml = re.sub(r'^\s*<\?xml[^>]*\?>', '', feed_xml, count=1)
        root = ET.fromstring(feed_xml)
        for item in root.iter("item"):
            link_el = item.find("link")
            if link_el is not None and link_el.text:
                link = link_el.text.strip()
                slug = link.rstrip("/").rsplit("/", 1)[-1].lower()
                if link not in seen and slug not in EXCLUDE_SLUGS:
                    seen.add(link)
                    urls.append(link)
    except Exception:
        pass

    # Source 2: server-rendered "Featured Events" carousel on /events/.
    try:
        html = base.get(URL)
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not EVENT_URL_RE.match(href):
                continue
            slug = href.rstrip("/").rsplit("/", 1)[-1].lower()
            if slug in EXCLUDE_SLUGS or href in seen:
                continue
            seen.add(href)
            urls.append(href)
    except Exception:
        pass

    return urls


def _extract_blocks(text):
    """Split page text into labeled sections (Time/Location/Fee/...).

    Works purely on line text rather than CSS classes/tags, since the exact
    markup of the meta block couldn't be directly inspected. Once a label's
    block is closed (a different label follows it), later reoccurrences of
    that same label (e.g. inside a "related events" widget further down the
    page) are ignored rather than re-opened.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    blocks = {}
    current = None
    closed = set()
    label_set = set(LABELS)
    for line in lines:
        key = line.rstrip(":").strip()
        if key in label_set:
            if key in closed:
                current = None
                continue
            if current and current != key:
                closed.add(current)
            current = key
            blocks.setdefault(current, [])
            continue
        if current:
            blocks[current].append(line)
    return blocks


def _parse_time_instances(lines):
    """Parse the Time: block into (start, end) datetime pairs.

    Handles the common "date line" + "HH:MMAM - HH:MMPM line" pattern, and
    makes a best effort at date *ranges* (treated as a single instance
    spanning start-date/start-time to end-date/end-time, since there's no
    reliable way to infer a weekday-recurrence rule from the rendered page
    alone). Distinct date+time pairs are always yielded as separate events.
    """
    results = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        start_t = end_t = None
        range_m = TIME_RANGE_RE.search(line)
        if range_m:
            date_text = line[:range_m.start()].strip(" ,-")
            start_t, end_t = range_m.group(1), range_m.group(2)
            i += 1
        else:
            date_text = line
            if i + 1 < n:
                nxt = lines[i + 1]
                range_m2 = TIME_RANGE_RE.search(nxt)
                if range_m2:
                    start_t, end_t = range_m2.group(1), range_m2.group(2)
                    i += 2
                else:
                    single_m = TIME_SINGLE_RE.search(nxt)
                    if single_m:
                        start_t = single_m.group(1)
                        i += 2
                    else:
                        i += 1
            else:
                i += 1

        start_date_text, end_date_text = date_text, None
        if " - " in date_text:
            parts = [p.strip() for p in date_text.split(" - ", 1)]
            if len(parts) == 2 and _looks_like_date(parts[0]) and _looks_like_date(parts[1]):
                start_date_text, end_date_text = parts

        if not _looks_like_date(start_date_text):
            continue

        try:
            start_date = dateutil_parser.parse(start_date_text, fuzzy=True)
        except (ValueError, OverflowError, TypeError):
            continue

        end_date = None
        if end_date_text:
            try:
                end_date = dateutil_parser.parse(end_date_text, fuzzy=True)
            except (ValueError, OverflowError, TypeError):
                end_date = None

        start_dt = start_date
        if start_t:
            try:
                start_dt = dateutil_parser.parse(start_t, default=start_date)
            except (ValueError, OverflowError, TypeError):
                start_dt = start_date

        end_dt = None
        if end_t:
            base_date = end_date or start_date
            try:
                end_dt = dateutil_parser.parse(end_t, default=base_date)
            except (ValueError, OverflowError, TypeError):
                end_dt = None
        elif end_date:
            end_dt = end_date

        results.append((start_dt, end_dt))

    return results


def _parse_fee(lines):
    if not lines:
        return "free", ""
    text = " ".join(lines).strip()
    amounts = [float(m.replace(",", "")) for m in MONEY_RE.findall(text)]
    if amounts:
        if max(amounts) == 0:
            return "free", "Free"
        return "paid", text
    lowered = text.lower()
    if "free" in lowered or "no cost" in lowered or "no charge" in lowered:
        return "free", text or "Free"
    return "paid", text


def _find_park_link_title(soup):
    """Look for a /parks-and-trails/{slug}/ link with a title attribute --
    this consistently held the canonical full park name in samples checked
    (e.g. title="Brookside Gardens"), which is more reliable than the raw
    Location: block text when that text is abbreviated.
    """
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/parks-and-trails/" in href:
            title = (a.get("title") or "").strip()
            if title and len(title) < 80:
                return title
    return None


def _venue_matches(raw, candidate):
    if not raw:
        return True
    r = raw.lower()
    c = candidate.lower()
    if r in c or c in r:
        return True
    return any(w in c for w in r.split() if len(w) > 3)


def _determine_place(venue):
    v = (venue or "").lower()
    for kw in INDOOR_KEYWORDS:
        if kw in v:
            return "indoor"
    return "outdoor"


def _parse_event_page(url):
    html = base.get(url)
    soup = BeautifulSoup(html, "html.parser")

    if soup.head:
        soup.head.decompose()
    for tag in soup(["script", "style"]):
        tag.decompose()

    h1 = soup.find("h1")
    if not h1:
        return []
    title = h1.get_text(" ", strip=True)
    if not title:
        return []

    full_text = soup.get_text("\n")
    idx = full_text.find(title)
    relevant_text = full_text[idx:] if idx != -1 else full_text

    blocks = _extract_blocks(relevant_text)

    location_lines = blocks.get("Location", [])
    venue_raw = location_lines[0] if location_lines else ""
    park_title = _find_park_link_title(soup)

    venue = venue_raw
    if park_title and (not venue_raw or _venue_matches(venue_raw, park_title)):
        venue = park_title
    if not venue:
        venue = NAME

    cost_type, cost_label = _parse_fee(blocks.get("Fee", []))
    age = " ".join(blocks.get("Age Range", [])).strip()
    place = _determine_place(venue)

    instances = _parse_time_instances(blocks.get("Time", []))
    if not instances:
        return []

    description = ""
    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        if len(t) < 40:
            continue
        if len(t) < 150 and DATE_LINE_RE.search(t):
            continue
        description = t
        break

    events = []
    for start, end in instances:
        if start is None:
            continue
        events.append({
            "name": title,
            "start": start,
            "end": end,
            "venue": venue,
            "description": description,
            "url": url,
            "cost_type": cost_type,
            "cost_label": cost_label,
            "age": age,
            "venue_key": None,
            "place": place,
            "source": ID,
        })
    return events


def fetch():
    urls = _collect_event_urls()
    today = date.today()
    results = []
    for url in urls[:80]:
        try:
            events = _parse_event_page(url)
        except Exception:
            continue
        for ev in events:
            start = ev.get("start")
            if not start:
                continue
            try:
                if start.date() < today:
                    continue
            except Exception:
                continue
            results.append(ev)
    return results
```

A couple of things worth testing once it's in your repo, since I couldn't execute this against the live site (my network access here is restricted to a handful of package registries, not montgomeryparks.org):

- Run `fetch()` and eyeball a few `venue` values against your recognized-park list — the `/parks-and-trails/` link heuristic worked cleanly on the one page I inspected in full, but I'd want to see it against a Wheaton/Cabin John/nature-center page before trusting it fully.
- If you need the full "All Events" calendar (not just the ~30 RSS/featured events), someone will need to open devtools on `/events/`, click "Load More Events", and grab the actual request URL — that's the one lead I couldn't chase down from here.
