# 2. National Building Museum - output below

I fetched the page and inspected what my tooling could see. Two things worth knowing before you drop this in:

**What I confirmed:** NBM's site emits `tec-api-origin` / `tec-api-version` meta tags, which means it runs **The Events Calendar (TEC)** WordPress plugin — that's a very well-documented, standardized plugin, and it's also the likely explanation for your JSON-LD miss: TEC has historically emitted event structured data as inline **Schema.org microdata** (`itemscope`/`itemprop` attributes) rather than a `<script type="application/ld+json">` block, so a JSON-LD-only extractor would legitimately find nothing even though structured data is present in the DOM.

**What I couldn't confirm:** my fetch tool runs the page through a readability-style extractor that, for this URL, dropped the entire event-listing section (it jumped straight from nav to footer) regardless of extraction mode I tried. I could not get raw DOM back to check exact class names against a live copy.

Given that, I built the parser around TEC's documented, stable patterns with layered fallbacks rather than one brittle selector set: (1) Schema.org microdata scoped correctly per event (ignoring nested Place/Offer scopes), (2) TEC's standard "Views v2" List View CSS classes, (3) generic heading/`<time>` heuristics as a last resort. It also does light recurring-event expansion, a year-rollover safety net for dates printed without a year, and de-dupes.

**Please run it against the live page first** — if it comes back empty, that means NBM's actual template diverges from documented TEC markup, and I'll need you to paste a snippet of the real HTML around one event card so I can fix the selectors precisely.

```python
"""Scraper for the National Building Museum's Programs & Events page.

https://www.nbm.org/programs-events/

The site runs The Events Calendar (TEC) WordPress plugin (confirmed via the
`tec-api-origin` / `tec-api-version` meta tags served on the page). TEC has
long emitted Schema.org structured data as inline microdata
(`itemscope`/`itemprop="startDate"` etc.) rather than JSON-LD, which is the
likely reason a JSON-LD-only extractor found nothing here even though
structured data exists in the DOM.

Parsing strategy, in priority order:
  1. Schema.org microdata (`itemscope` + `itemtype` containing "Event"),
     read with scope-awareness so a nested Place/Offer's `itemprop="name"`
     doesn't get mistaken for the event's own name.
  2. TEC's "Views v2" List View CSS classes
     (`.tribe-events-calendar-list__event*`), which is TEC's current
     default frontend template.
  3. Generic heading + <time> heuristics, as a last-resort fallback.

Known limitation: this was written without the ability to inspect NBM's
live raw HTML (the fetch tooling available at write-time stripped the
event-listing section entirely, likely a readability/extraction artifact
rather than proof the markup differs from TEC's documented output). Run
`fetch()` against the real page first; if it returns an empty list, TEC's
markup on this install has diverged from the documented patterns above and
the selectors in `_find_event_roots` / `_extract_*` need a tweak against
the actual DOM.
"""

import re
from datetime import datetime, timedelta

from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

from . import base

ID = "national-building-museum"
NAME = "National Building Museum"
URL = "https://www.nbm.org/programs-events/"

_VENUE_KEY = "national-building-museum"
_DEFAULT_VENUE = "National Building Museum"
_SOURCE = ID

_PRICE_RE = re.compile(r"\$\s?\d[\d,.]*")
_AGE_RE = re.compile(
    r"(ages?\s*\d{1,2}\s*(?:[-\u2013+]\s*\d{0,2})?"
    r"|all ages"
    r"|adults?\s*only"
    r"|family[- ]friendly"
    r"|\b\d{1,2}\+"
    r"|recommended for ages [^.;\n]+)",
    re.IGNORECASE,
)

_WEEKDAY_NAMES = [
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
]
_RECUR_RE = re.compile(
    r"every\s+(" + "|".join(_WEEKDAY_NAMES) + r")", re.IGNORECASE
)
_THROUGH_RE = re.compile(
    r"(?:through|thru|until|ending)\s+"
    r"([A-Za-z]+\.?\s+\d{1,2}(?:,\s*\d{4})?|\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)
# Heuristic cap on generated recurring instances when no explicit end date
# is found in the page text. Tune once real markup is confirmed.
_MAX_RECUR_INSTANCES = 12


def _text(el):
    """Collapse an element's visible text to single-spaced, stripped text."""
    if el is None:
        return ""
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()


def _scoped_itemprop(root, prop):
    """Find the first descendant with itemprop==prop that belongs directly
    to `root`'s microdata scope (i.e. isn't inside a nested itemscope, such
    as a Place or Offer nested inside an Event)."""
    for el in root.find_all(attrs={"itemprop": prop}):
        ancestor = el.parent
        nested = False
        while ancestor is not None and ancestor is not root:
            if ancestor.has_attr("itemscope"):
                nested = True
                break
            ancestor = ancestor.parent
        if not nested:
            return el
    return None


def _microdata_value(el):
    if el is None:
        return ""
    if el.name == "meta":
        return (el.get("content") or "").strip()
    if el.name == "time":
        return (el.get("datetime") or _text(el)).strip()
    if el.has_attr("content"):
        return el["content"].strip()
    return _text(el)


def _parse_dt(value, reference=None):
    if not value:
        return None
    value = value.strip().replace(" @ ", " ")
    if not value:
        return None
    try:
        return dateutil_parser.parse(value, default=reference or datetime.now())
    except (ValueError, OverflowError):
        return None


def _fix_year_rollover(dt, today):
    """TEC list views often print dates without a year (e.g. 'September 10
    @ 6:00 pm'), and dateutil defaults missing fields to today's date. If
    that produces something more than a week in the past, assume the year
    should have rolled forward (the page listed an upcoming event, not a
    stale one)."""
    if dt is None:
        return dt
    if dt.date() < today - timedelta(days=7):
        try:
            return dt.replace(year=dt.year + 1)
        except ValueError:
            # e.g. Feb 29 landing on a non-leap year.
            return dt + timedelta(days=365)
    return dt


def _find_event_roots(soup):
    roots = [
        tag
        for tag in soup.find_all(attrs={"itemscope": True})
        if tag.has_attr("itemtype") and "Event" in tag["itemtype"]
    ]
    if roots:
        return roots

    roots = soup.select(".tribe-events-calendar-list__event")
    if roots:
        return roots

    # Loosest fallback: classic TEC / hCalendar-style markup.
    return soup.select(".hentry.vevent, .type-tribe_events")


def _extract_name(root):
    el = _scoped_itemprop(root, "name")
    if el is not None:
        text = _text(el)
        if text:
            return text
    heading = root.find(["h1", "h2", "h3", "h4"])
    if heading is not None:
        text = _text(heading)
        if text:
            return text
    link = root.find("a")
    return _text(link) if link is not None else ""


def _extract_url(root, base_url):
    el = _scoped_itemprop(root, "url")
    href = None
    if el is not None:
        href = el.get("href") or el.get("content") or _text(el)
    if not href:
        link = root.select_one(
            ".tribe-events-calendar-list__event-title-link, "
            "a[rel='bookmark'], h1 a, h2 a, h3 a, h4 a"
        )
        if link is not None:
            href = link.get("href")
    if not href:
        return ""
    return urljoin(base_url, href.strip())


def _extract_start_end(root):
    start = end = None

    start_el = _scoped_itemprop(root, "startDate")
    if start_el is not None:
        start = _parse_dt(_microdata_value(start_el))

    end_el = _scoped_itemprop(root, "endDate")
    if end_el is not None:
        end = _parse_dt(_microdata_value(end_el))

    if start is None:
        for t in root.select(
            ".tribe-events-calendar-list__event-datetime-wrapper time, "
            ".tribe-event-date-start, .tribe-events-schedule__date, time"
        ):
            candidate = _parse_dt(t.get("datetime") or _text(t))
            if candidate is not None:
                start = candidate
                break

    if end is None and start is not None:
        wrapper = root.select_one(
            ".tribe-events-calendar-list__event-datetime-wrapper"
        )
        if wrapper is not None:
            end_span = wrapper.select_one(".tribe-event-time")
            if end_span is not None:
                end = _parse_dt(_text(end_span), reference=start)

    return start, end


def _extract_venue(root):
    loc_el = _scoped_itemprop(root, "location")
    if loc_el is not None:
        name_el = loc_el.find(attrs={"itemprop": "name"})
        if name_el is not None:
            text = _text(name_el)
            if text:
                return text

    venue_el = root.select_one(
        ".tribe-events-calendar-list__event-venue-title, "
        ".tribe-events-venue-details, .tribe-venue"
    )
    if venue_el is not None:
        text = _text(venue_el)
        if text:
            return text

    return _DEFAULT_VENUE


def _extract_description(root):
    el = _scoped_itemprop(root, "description")
    if el is not None:
        text = _text(el)
        if text:
            return text

    el = root.select_one(
        ".tribe-events-calendar-list__event-description, .entry-summary, .summary"
    )
    if el is not None:
        return _text(el)

    return ""


def _extract_cost(root):
    cost_el = root.select_one(
        ".tribe-events-calendar-list__event-cost, .tribe-events-event-cost"
    )
    label = _text(cost_el) if cost_el is not None else ""

    if not label:
        offers_el = _scoped_itemprop(root, "offers")
        if offers_el is not None:
            label = _text(offers_el)

    if not label:
        block_text = _text(root)
        m = _PRICE_RE.search(block_text)
        if m:
            label = m.group(0)
        elif re.search(r"\bfree\b", block_text, re.IGNORECASE):
            label = "Free"

    if not label:
        # No cost info found anywhere on the card. NBM's public programs
        # skew free-with-RSVP, so default to "free" -- but this is a guess;
        # tighten it once real cards are visible.
        return "free", ""

    if _PRICE_RE.search(label):
        # Catches "Members free / $12 non-members": a price is mentioned
        # for at least one audience, so treat the event as paid overall.
        return "paid", label
    if re.search(r"\bfree\b", label, re.IGNORECASE):
        return "free", label
    return "free", label


def _extract_age(root):
    m = _AGE_RE.search(_text(root))
    return m.group(0).strip() if m else ""


def _build_event(root, base_url):
    name = _extract_name(root)
    if not name:
        return None

    start, end = _extract_start_end(root)
    if start is None:
        return None

    return {
        "name": name,
        "start": start,
        "end": end,
        "venue": _extract_venue(root),
        "description": _extract_description(root),
        "url": _extract_url(root, base_url),
        "cost_type": _extract_cost(root)[0],
        "cost_label": _extract_cost(root)[1],
        "age": _extract_age(root),
        "venue_key": _VENUE_KEY,
        "place": "indoor",
        "source": _SOURCE,
    }


def _expand_recurring(event, block_text):
    """If the card text reads like 'every Saturday ... through <date>',
    expand into one dict per weekly occurrence. Otherwise return the event
    unchanged. This only fires on an explicit 'every <weekday>' phrase, so
    normal single-date cards are never affected."""
    if event["start"] is None:
        return [event]

    if not _RECUR_RE.search(block_text):
        return [event]

    through_match = _THROUGH_RE.search(block_text)
    range_end = _parse_dt(through_match.group(1)) if through_match else None
    if range_end is None:
        range_end = event["start"] + timedelta(weeks=_MAX_RECUR_INSTANCES - 1)

    duration = (event["end"] - event["start"]) if event["end"] else None

    instances = []
    cursor = event["start"]
    count = 0
    while cursor.date() <= range_end.date() and count < _MAX_RECUR_INSTANCES:
        inst = dict(event)
        inst["start"] = cursor
        inst["end"] = (cursor + duration) if duration else None
        instances.append(inst)
        cursor = cursor + timedelta(weeks=1)
        count += 1

    return instances or [event]


def _is_past(start, today):
    return start.date() < today


def fetch() -> list[dict]:
    html = base.get(URL)
    soup = BeautifulSoup(html, "html.parser")
    roots = _find_event_roots(soup)

    today = datetime.now().date()

    raw_events = []
    for root in roots:
        event = _build_event(root, URL)
        if event is None:
            continue

        event["start"] = _fix_year_rollover(event["start"], today)
        if event["end"] is not None:
            event["end"] = _fix_year_rollover(event["end"], today)

        block_text = _text(root)
        raw_events.extend(_expand_recurring(event, block_text))

    seen = set()
    events = []
    for event in raw_events:
        if _is_past(event["start"], today):
            continue
        key = (event["name"], event["start"], event["url"])
        if key in seen:
            continue
        seen.add(key)
        events.append(event)

    return events


if __name__ == "__main__":
    found = fetch()
    print(f"{len(found)} event(s) found\n")
    for evt in found:
        print(f"{evt['start']}  {evt['name']}  [{evt['cost_type']}] {evt['cost_label']!r}")
```

If it returns 0 events when you run it live, the most likely culprits are (a) NBM's actual TEC theme uses different class names than the documented `Views v2` set, or (b) `/programs-events/` is a landing page whose real dated listings live one level down (e.g. `/adult-programs/`, `/programs-events/kids-programs/`) — worth checking those URLs too if the top-level page comes up empty.

