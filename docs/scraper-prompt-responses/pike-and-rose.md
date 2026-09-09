# 4. Pike & Rose - output below

Let me build and sanity-test the scraper logic locally before finalizing, since I can only see this site's rendered text (not raw tag names) through fetch tools — I'll design the parser to work off text content and anchor attributes rather than fragile CSS selectors, then verify it against synthetic HTML that mirrors the real page's text structure.I found a real bug via testing: my naive "bump to next year if before today" rule breaks ongoing multi-week ranges (a farmers market that started in the past but runs into the future was getting shoved a whole year forward). Let me fix the date-inference and the non-recurring fallback logic.Now let's fix `_infer_range_dates` and add the `_resolve_detail_date` helper:Now let's copy the fixed module into the test package and update the test's expectations to match the corrected (more accurate) behavior:This all looks correct now — 25 sensible events, correct years, correct weekday-based expansion for the farmers market and Live Music Fridays, correct monthly handling for PIKEKids, and sane continuous-range fallback for the ambiguous multi-week items (Skinceuticals, Kids Club). Let me quickly test a couple of edge cases (network failure on a detail page, missing title attribute) before finalizing.This all looks correct. Let me do one last check for basic syntax/import cleanliness (unused imports, etc.) before delivering.Clean. Here's the complete module:Everything checks out. Here's the full file, ready to paste into `scripts/scrapers/pike_and_rose.py`:

```python
"""Scraper for the Pike & Rose events page.

Pike & Rose (pikeandrose.com) runs on WordPress/Elementor. Its events listing
page does NOT expose usable Schema.org/JSON-LD event data (a prior attempt
using JSON-LD extraction returned 0 events), so this scraper parses the
rendered page instead.

Rather than hard-coding CSS class names for a theme we can't fully inspect
ahead of time, the parsing here leans on two things that are stable and easy
to verify from the page's *content*:

1. On the listing page, each event card is a single ``<a href="/event/…">``
   whose ``title`` attribute is WordPress's standard
   ``"Permalink to {Title}"`` string -- a reliable, structure-independent way
   to recover the exact event title even though the card's visible text
   (date range + title + venue) is otherwise all run together.

2. On each individual event page, the visible text -- extracted line by line
   via ``get_text()`` -- follows a consistent order: Title, then Venue, then
   (optionally) a "Weekday, Month Day | start-end time" line, then the
   description, then a "Share" / "Other upcoming events" footer. This lets
   us pull venue, date, time and description without depending on specific
   tag/class names, which we have no reliable way to confirm remotely.

Because the listing page only shows a start/end *month-day* pair (no year)
and the individual event pages likewise print dates with no year, years are
inferred: a date is assumed to fall in the current year unless that would
put it in the past, in which case it's rolled forward to next year.

Recurring events (weekly farmers market, "Live Music Fridays", the monthly
"PIKEKids" series, etc.) are only expanded into multiple date instances when
the page gives us solid evidence of the cadence (an explicit "every Friday"
/ "last Saturday of every month" phrase, or the event being a farmers/farm
market, which are always weekly). Otherwise a single occurrence is returned
using the specific date on the event's own page, since guessing a cadence
that turns out to be wrong (e.g. assuming weekly when it's actually monthly,
as PIKEKids is) is worse than under-covering.

Note: the listing page has a "Load more events" control that almost
certainly pages in more events via JS/AJAX. Only the events present in the
initial server-rendered HTML are scraped here.
"""

from __future__ import annotations

import calendar
import re
import time as _time
from datetime import date, datetime, time, timedelta
from urllib.parse import urljoin

import dateutil.parser as dtparser
from bs4 import BeautifulSoup

from . import base

ID = "pike-and-rose"
NAME = "Pike & Rose"
URL = "https://www.pikeandrose.com/events"

# Be polite between the extra per-event page fetches.
_DETAIL_FETCH_DELAY_SECONDS = 0.25

_WEEKDAYS = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
_MONTH_ABBR = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
_MONTH_FULL = (
    "January|February|March|April|May|June|July|August|September|October"
    "|November|December"
)

# "JAN 1 - JAN 4" / "OCT 4" prefix on the listing page's event links.
_LIST_DATE_RE = re.compile(
    rf"^({_MONTH_ABBR})\w*\.?\s+(\d{{1,2}})"
    rf"(?:\s*-\s*({_MONTH_ABBR})\w*\.?\s+(\d{{1,2}}))?",
    re.IGNORECASE,
)

# "Sunday, October 4" / "Sunday, October 4 - Sunday, October 11" plus an
# optional "| 11am-4pm" time suffix, on an individual event page.
_DETAIL_DATE_RE = re.compile(
    rf"^({_WEEKDAYS}),?\s+({_MONTH_FULL})\s+(\d{{1,2}})"
    rf"(?:\s*-\s*({_WEEKDAYS}),?\s+({_MONTH_FULL})\s+(\d{{1,2}}))?"
    rf"(?:\s*\|\s*(.+))?$",
    re.IGNORECASE,
)

_TIME_TOKEN = r"\d{1,2}(?::\d{2})?\s*[APap]\.?[Mm]\.?"
_TIME_RANGE_RE = re.compile(rf"({_TIME_TOKEN})\s*(?:-|–|to)\s*({_TIME_TOKEN})")
_SINGLE_TIME_RE = re.compile(rf"({_TIME_TOKEN})")

_EVERY_WEEKDAY_RE = re.compile(rf"\bevery\s+({_WEEKDAYS})s?\b", re.IGNORECASE)
_NTH_WEEKDAY_MONTH_RE = re.compile(
    rf"\b(last|first|second|third|fourth)\s+({_WEEKDAYS})\s+of\s+(?:every|each)\s+month\b",
    re.IGNORECASE,
)
_FARM_MARKET_RE = re.compile(r"farm(?:ers)?\s+market", re.IGNORECASE)

_FREE_RE = re.compile(
    r"\badmission[^.]{0,20}\bfree\b|\bfree\b[^.]{0,20}\badmission\b"
    r"|\bfree\s+(?:and\s+open|event|to\s+attend|entry)\b",
    re.IGNORECASE,
)
_PRICE_RE = re.compile(r"\$\d+(?:\.\d{2})?")
_AGE_21_RE = re.compile(r"\b21\s*\+|\b21\s*and\s*over\b|\bmust\s+be\s+21\b", re.IGNORECASE)
_ALL_AGES_RE = re.compile(r"\ball\s+ages\b|\bfamily[- ]friendly\b|\bkids\b", re.IGNORECASE)
_INDOOR_RE = re.compile(r"\bindoor\b|\bin[- ]store\b|\binside\b", re.IGNORECASE)
_OUTDOOR_RE = re.compile(
    r"\boutdoor\b|\bpatio\b|\boutside\b|\blawn\b|\bparking\s+lot\b", re.IGNORECASE
)

_STOP_MARKERS = {"share", "other upcoming events", "sign up"}

_WEEKDAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def fetch() -> list[dict]:
    today = datetime.now().date()

    html = base.get(URL)
    soup = BeautifulSoup(html, "html.parser")
    items = _parse_listing(soup)

    results: list[dict] = []
    for item in items:
        detail = None
        try:
            detail_html = base.get(item["url"])
            detail = _parse_detail_page(detail_html, item["title"])
        except Exception:
            detail = None
        finally:
            _time.sleep(_DETAIL_FETCH_DELAY_SECONDS)

        venue = (detail["venue"] if detail and detail["venue"] else item["venue_guess"]) or NAME
        description = detail["description"] if detail else ""

        start_date, end_date = _infer_range_dates(
            item["start_month"], item["start_day"], item["end_month"], item["end_day"], today
        )
        if start_date is None:
            continue

        start_time = detail["start_time"] if detail else None
        end_time = detail["end_time"] if detail else None

        # The individual event page usually only prints one specific date
        # (often just the *first* occurrence, which may already be in the
        # past even though the series/listing is still ongoing). Resolve
        # its month/day against the year(s) already chosen for the listing
        # range rather than re-inferring a year independently -- otherwise
        # an ongoing series that started earlier this year gets wrongly
        # bumped a whole year forward.
        detail_date = None
        if detail and detail["start_date"]:
            dm, dd = detail["start_date"]
            if dm and dd:
                detail_date = _resolve_detail_date(dm, dd, start_date, end_date)

        scan_text = " ".join(
            filter(None, [item["title"], venue, description, detail["scan_text"] if detail else ""])
        )

        recurrence = _detect_recurrence(item["title"], venue, scan_text)
        is_ranged = bool(end_date and end_date != start_date)

        if recurrence and is_ranged and end_date > start_date + timedelta(days=6):
            weekday = _resolve_weekday(recurrence, detail_date or start_date)
            if recurrence["type"] == "weekly":
                occurrences = _weekly_occurrences(start_date, end_date, weekday)
            else:
                occurrences = _monthly_nth_weekday_occurrences(
                    start_date, end_date, recurrence["nth"], weekday
                )
            for occ in occurrences:
                if occ < today:
                    continue
                results.append(
                    _build_event(
                        item["title"], venue, description, item["url"],
                        occ, None, start_time, end_time, scan_text,
                    )
                )
        elif is_ranged:
            # A multi-day/week listing with no confirmed recurrence cadence
            # (e.g. a season-long in-store promo). Represent it as one
            # continuous event spanning the listing's stated window rather
            # than pinning it to the individual page's date, which is often
            # just the original launch day and may already be stale.
            if end_date < today:
                continue
            results.append(
                _build_event(
                    item["title"], venue, description, item["url"],
                    start_date, end_date, start_time, end_time, scan_text,
                )
            )
        else:
            occ_start = detail_date or start_date
            if occ_start < today:
                continue
            results.append(
                _build_event(
                    item["title"], venue, description, item["url"],
                    occ_start, None, start_time, end_time, scan_text,
                )
            )

    results.sort(key=lambda e: e["start"])
    return results


# --------------------------------------------------------------------------
# Listing page parsing
# --------------------------------------------------------------------------


def _parse_listing(soup: BeautifulSoup) -> list[dict]:
    seen: dict[str, dict] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not re.search(r"/event/[^/]+/?$", href):
            continue
        href = urljoin(URL, href)
        if href in seen:
            continue

        title_attr = a.get("title", "") or ""
        title = re.sub(r"^Permalink to\s+", "", title_attr, flags=re.IGNORECASE).strip()
        full_text = a.get_text(strip=True)

        m = _LIST_DATE_RE.match(full_text)
        start_month = start_day = end_month = end_day = None
        venue_guess = ""
        if m:
            mon1, day1, mon2, day2 = m.groups()
            start_month = _month_num(mon1)
            start_day = int(day1)
            if mon2 and day2:
                end_month = _month_num(mon2)
                end_day = int(day2)
            remainder = full_text[m.end():].strip()
            if title and remainder.lower().startswith(title.lower()):
                venue_guess = remainder[len(title):].strip()
            elif not title:
                title = remainder
        elif not title:
            title = full_text

        if not title or start_month is None:
            # Couldn't get enough to build an event (e.g. an image-only
            # link with no title attribute and no leading date) -- skip,
            # a sibling link for the same card usually has the real data.
            continue

        seen[href] = {
            "url": href,
            "title": title,
            "venue_guess": venue_guess,
            "start_month": start_month,
            "start_day": start_day,
            "end_month": end_month,
            "end_day": end_day,
        }
    return list(seen.values())


# --------------------------------------------------------------------------
# Individual event page parsing
# --------------------------------------------------------------------------


def _parse_detail_page(html: str, title_hint: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    lines = [ln.strip() for ln in soup.get_text("\n").split("\n")]
    lines = [ln for ln in lines if ln]

    idx = None
    if title_hint:
        for i, ln in enumerate(lines):
            if ln.lower() == title_hint.lower():
                idx = i
                break
    if idx is None:
        for i, ln in enumerate(lines):
            if ln.lower() == "back to events":
                idx = i + 1
                break
    if idx is None:
        idx = 0

    venue = ""
    j = idx + 1
    if j < len(lines) and len(lines[j]) < 60 and not _DETAIL_DATE_RE.match(lines[j]):
        venue = lines[j]
        j += 1

    start_date = end_date = None
    start_time = end_time = None
    if j < len(lines):
        m = _DETAIL_DATE_RE.match(lines[j])
        if m:
            _wd1, mon1, day1, _wd2, mon2, day2, time_part = m.groups()
            start_date = _parse_month_day(mon1, day1)
            if mon2 and day2:
                end_date = _parse_month_day(mon2, day2)
            if time_part:
                start_time, end_time = _parse_time_range(time_part)
            j += 1

    desc_lines = []
    for ln in lines[j:]:
        low = ln.lower()
        if low in _STOP_MARKERS or low.startswith("want to know") or ln.startswith("http"):
            break
        desc_lines.append(ln)
        if len(desc_lines) >= 25:
            break
    description = " ".join(desc_lines).strip()

    scan_text = " ".join(lines[idx: idx + 60])

    return {
        "venue": venue,
        "start_date": start_date,
        "end_date": end_date,
        "start_time": start_time,
        "end_time": end_time,
        "description": description,
        "scan_text": scan_text,
    }


# --------------------------------------------------------------------------
# Date / time helpers
# --------------------------------------------------------------------------


def _month_num(abbr: str) -> int | None:
    try:
        return dtparser.parse(f"{abbr} 1 2000").month
    except (ValueError, OverflowError):
        return None


def _parse_month_day(month_name: str, day_str: str):
    try:
        dt = dtparser.parse(f"{month_name} {day_str} 2000")
        return dt.month, dt.day
    except (ValueError, OverflowError):
        return None


def _parse_time_range(time_part: str):
    m = _TIME_RANGE_RE.search(time_part)
    if m:
        return _make_time(m.group(1)), _make_time(m.group(2))
    m = _SINGLE_TIME_RE.search(time_part)
    if m:
        return _make_time(m.group(1)), None
    return None, None


def _make_time(token: str) -> time | None:
    try:
        return dtparser.parse(token).time()
    except (ValueError, OverflowError):
        return None


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _infer_range_dates(start_month, start_day, end_month, end_day, today: date):
    """Resolve a year-less month/day (or month/day range) to real dates.

    The page never prints a year, so we assume the current year unless the
    resulting date (or, for a range, the *end* of the range) would fall
    fully in the past -- in which case the whole thing is rolled forward a
    year. Only checking the end of the range (not the start) matters: an
    ongoing multi-week series that started earlier this year but is still
    running (end date still ahead of today) must stay in the current year,
    not get bumped just because its start date has already passed.
    """
    if start_month is None or start_day is None:
        return None, None

    start = _safe_date(today.year, start_month, start_day)
    if start is None:
        return None, None

    if end_month is None or end_day is None:
        if start < today:
            bumped = _safe_date(today.year + 1, start_month, start_day)
            if bumped:
                start = bumped
        return start, start

    end = _safe_date(start.year, end_month, end_day)
    if end is None:
        end = start
    if end < start:
        # Range wraps across a year boundary (e.g. "NOV 1 - JAN 5").
        end = _safe_date(start.year + 1, end_month, end_day) or end

    if end < today:
        # The whole range, as currently dated, is already over -- shift
        # both ends forward a year.
        bumped_start = _safe_date(start.year + 1, start_month, start_day)
        if bumped_start:
            start = bumped_start
        end = _safe_date(start.year, end_month, end_day) or end
        if end < start:
            end = _safe_date(start.year + 1, end_month, end_day) or end

    return start, end


def _resolve_detail_date(month, day, start_date: date, end_date: date):
    """Pick whichever year (matching the already-resolved listing range)
    makes this month/day fall inside [start_date, end_date]."""
    candidate = _safe_date(start_date.year, month, day)
    if candidate and start_date <= candidate <= end_date:
        return candidate
    if end_date.year != start_date.year:
        candidate2 = _safe_date(end_date.year, month, day)
        if candidate2 and start_date <= candidate2 <= end_date:
            return candidate2
    return candidate or start_date


def _weekly_occurrences(start_date: date, end_date: date, weekday: int) -> list[date]:
    offset = (weekday - start_date.weekday()) % 7
    d = start_date + timedelta(days=offset)
    out = []
    while d <= end_date:
        out.append(d)
        d += timedelta(days=7)
    return out


def _nth_weekday_of_month(year: int, month: int, nth: str, weekday: int) -> date | None:
    cal = calendar.Calendar()
    days = [d for d in cal.itermonthdates(year, month) if d.month == month and d.weekday() == weekday]
    if not days:
        return None
    if nth == "last":
        return days[-1]
    idx = {"first": 0, "second": 1, "third": 2, "fourth": 3}.get(nth)
    if idx is None or idx >= len(days):
        return None
    return days[idx]


def _monthly_nth_weekday_occurrences(start_date: date, end_date: date, nth: str, weekday: int) -> list[date]:
    out = []
    y, m = start_date.year, start_date.month
    while (y, m) <= (end_date.year, end_date.month):
        d = _nth_weekday_of_month(y, m, nth, weekday)
        if d and start_date <= d <= end_date:
            out.append(d)
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def _resolve_weekday(recurrence: dict, reference_date: date) -> int:
    weekday_name = recurrence.get("weekday")
    if weekday_name:
        return _WEEKDAY_INDEX[weekday_name.lower()]
    return reference_date.weekday()


# --------------------------------------------------------------------------
# Recurrence / cost / age / place detection
# --------------------------------------------------------------------------


def _detect_recurrence(title: str, venue: str, text: str):
    m = _NTH_WEEKDAY_MONTH_RE.search(text)
    if m:
        nth, weekday = m.groups()
        return {"type": "monthly", "nth": nth.lower(), "weekday": weekday}

    m = _EVERY_WEEKDAY_RE.search(text)
    if m:
        return {"type": "weekly", "weekday": m.group(1)}

    if _FARM_MARKET_RE.search(f"{title} {venue}"):
        return {"type": "weekly", "weekday": None}

    return None


def _detect_cost(text: str) -> tuple[str, str]:
    if _FREE_RE.search(text):
        return "free", "Free"
    price_match = _PRICE_RE.search(text)
    if price_match and re.search(r"ticket", text, re.IGNORECASE):
        return "paid", f"From {price_match.group(0)}"
    return "free", "Free"


def _detect_age(text: str) -> str:
    if _AGE_21_RE.search(text):
        return "21+"
    if _ALL_AGES_RE.search(text):
        return "All ages"
    return ""


def _detect_place(text: str) -> str:
    if _INDOOR_RE.search(text):
        return "indoor"
    if _OUTDOOR_RE.search(text):
        return "outdoor"
    return "outdoor"


# --------------------------------------------------------------------------
# Event dict assembly
# --------------------------------------------------------------------------


def _build_event(name, venue, description, url, start_date, end_date, start_time, end_time, scan_text) -> dict:
    start_dt = datetime.combine(start_date, start_time or time(0, 0))

    if end_time and (end_date is None or end_date == start_date):
        end_dt = datetime.combine(start_date, end_time)
    elif end_date and end_date != start_date:
        end_dt = datetime.combine(end_date, end_time or time(0, 0))
    elif end_time:
        end_dt = datetime.combine(start_date, end_time)
    else:
        end_dt = None

    cost_type, cost_label = _detect_cost(scan_text)

    return {
        "name": name,
        "start": start_dt,
        "end": end_dt,
        "venue": venue or NAME,
        "description": description,
        "url": url,
        "cost_type": cost_type,
        "cost_label": cost_label,
        "age": _detect_age(scan_text),
        "venue_key": ID,
        "place": _detect_place(scan_text),
        "source": ID,
    }
```

**Why the previous JSON-LD approach failed and what this does instead:** the listing page has no usable Schema.org markup, so this parses rendered text. Two structural facts anchor the parsing without guessing at CSS classes: listing-page event links carry WordPress's standard `title="Permalink to {Title}"` attribute (recovers exact titles even though date/title/venue run together visually), and individual event pages present Title → Venue → optional "Weekday, Month Day | time" → description in a stable line order.

Worth knowing about the live site's data:
- **No year is ever printed**, so dates are inferred (current year, rolled to next year only if the *whole* range is already over — this matters so an in-progress farmers-market season doesn't get bumped a year just because it started months ago).
- **Recurrence is only expanded when there's real evidence** — an explicit "every Friday," a "last Saturday of every month" phrase, or a farmers/farm market (always weekly). I verified against the live pages that this matters: PIKEKids is monthly, not weekly, despite showing a multi-week range like a recurring series.
- Ambiguous multi-week listings with no confirmed cadence (e.g. a seasonal in-store promo) are returned as one continuous event spanning the listing's stated window rather than dropped or mis-expanded.
- The "Load more events" control likely paginates via JS/AJAX and isn't fetched — only the server-rendered events are scraped.

