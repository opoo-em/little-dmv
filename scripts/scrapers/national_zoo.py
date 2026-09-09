"""Scraper for Smithsonian National Zoo events.

The listing page (https://nationalzoo.si.edu/visit/events) only carries a
handful of "featured" upcoming events, plus a "Today at the Zoo" section of
open-ended recurring programs (daily demos, drop-in play) and a "Past
Events" archive. A prior attempt at Schema.org/JSON-LD extraction found
nothing on this site (it doesn't emit that markup), and the National Zoo is
not included in the main Smithsonian iCal feed -- hence this dedicated
scraper.

Strategy:

1. Parse the listing page to find the upcoming, dated events only (stopping
   before "Today at the Zoo" / "Past Events").
2. Visit each event's own page for the authoritative details: the listing
   page doesn't carry cost/age/location, and individual event pages use
   varying section labels for the same info ("Dates" vs. "Date and Time" vs.
   "When"; "Tickets and Parking" vs. "Admission"). Parsing is done by
   matching heading *text* in document order rather than relying on any
   particular CSS class or nesting depth, so it degrades gracefully if the
   markup structure shifts slightly.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from . import base

ID = "national-zoo"
NAME = "Smithsonian National Zoo"
URL = "https://nationalzoo.si.edu/events"

_SITE_ROOT = "https://nationalzoo.si.edu"

_EVENT_HREF_RE = re.compile(r"/visit/events/[a-z0-9][a-z0-9\-]*(?:[/?]|$)", re.I)

_SECTION_STOP_HEADINGS = {"today at the zoo", "past events"}

_DATE_LABELS = {"date", "dates", "date and time", "date & time", "when"}
_TIME_LABELS = {"time", "hours"}
_LOCATION_LABELS = {"location", "where"}
_COST_LABELS = {
    "admission",
    "cost",
    "price",
    "prices",
    "tickets",
    "tickets and parking",
    "tickets & parking",
    "admission and tickets",
    "admission & tickets",
}

_AGE_PATTERNS = [
    re.compile(r"ages?\s+\d{1,2}\s*(?:-|\u2013|to)\s*\d{1,2}", re.I),
    re.compile(r"adults[\s-]only", re.I),
    re.compile(r"all ages", re.I),
    re.compile(r"recommended for ages?\s*\d{1,2}\+?", re.I),
    re.compile(r"\b\d{1,2}\s*\+\s*(?:years?|yrs?)\b", re.I),
]

_INDOOR_KEYWORDS = (
    "house",
    "pavilion",
    "theater",
    "theatre",
    "auditorium",
    "building",
    "hall",
    "indoor",
    "discovery center",
    "discovery centre",
    "visitor center",
    "visitor centre",
    "center for",
    "lecture",
    "classroom",
)

_TICKET_CTA_RE = re.compile(r"\b(?:buy|get|book|purchase)\s+tickets\b", re.I)

_TIME_TOKEN_RE = re.compile(r"\d{1,2}(?::\d{2})?\s*[ap]m", re.I)

_MONTH_RE = (
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"
)
_MONTH_DAY_RE = re.compile(_MONTH_RE + r"\s+\d{1,2}", re.I)
_MONTH_NAME_RE = re.compile(_MONTH_RE, re.I)
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def _has_month_name(text: str) -> bool:
    return bool(_MONTH_NAME_RE.search(text))


def fetch() -> list[dict]:
    listing_html = base.get(URL)
    listing_soup = BeautifulSoup(listing_html, "html.parser")

    candidates = _collect_event_links(listing_soup)

    today = date.today()
    results: list[dict] = []

    for name, url in candidates[:40]:
        try:
            events = _scrape_event_page(url, fallback_name=name)
        except Exception:
            continue
        for item in events:
            end_ref = item["end"] or item["start"]
            if end_ref.date() < today:
                continue
            results.append(item)

    return results


# --------------------------------------------------------------------------
# Listing page
# --------------------------------------------------------------------------


def _collect_event_links(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Return ordered, deduped (name, absolute_url) pairs for the upcoming
    dated events on the listing page, stopping before the recurring
    "Today at the Zoo" programs and the "Past Events" archive."""
    h1 = soup.find("h1")
    anchor = h1 if h1 is not None else soup

    seen: set[str] = set()
    out: list[tuple[str, str]] = []

    for tag in anchor.find_all_next(["h1", "h2", "h3", "h4"]):
        heading_text = tag.get_text(" ", strip=True).strip().lower()
        if heading_text in _SECTION_STOP_HEADINGS:
            break

        link = tag.find("a", href=True)
        if not link:
            continue
        href = link["href"]
        if not _EVENT_HREF_RE.search(href):
            continue

        abs_url = urljoin(_SITE_ROOT, href)
        if abs_url in seen:
            continue

        name = link.get_text(" ", strip=True).rstrip(" \t\n\u203a\u00bb").strip()
        if not name:
            continue

        seen.add(abs_url)
        out.append((name, abs_url))

    return out


# --------------------------------------------------------------------------
# Event detail page
# --------------------------------------------------------------------------


def _content_blocks(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Return (tag_name, text) pairs for an event page's main content, in
    document order, starting after the <h1> title and stopping before the
    sitewide "Contact Us" footer that appears on every page."""
    h1 = soup.find("h1")
    if h1 is None:
        return []

    blocks: list[tuple[str, str]] = []
    for tag in h1.find_all_next(
        ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "dd", "dt"]
    ):
        text = tag.get_text(" ", strip=True)
        if not text:
            continue
        is_heading = tag.name in ("h1", "h2", "h3", "h4", "h5", "h6")
        if is_heading and text.strip().lower() == "contact us":
            break
        blocks.append((tag.name, text))
    return blocks


def _extract_section(blocks: list[tuple[str, str]], labels: set[str]) -> str:
    """Collect the text of all content blocks between a heading whose text
    matches `labels` and the next heading."""
    collecting = False
    values: list[str] = []
    for name, text in blocks:
        is_heading = name.startswith("h")
        if is_heading:
            if text.strip().lower() in labels:
                collecting = True
                continue
            if collecting:
                break
            continue
        if collecting:
            values.append(text)
    return " ".join(values).strip()


def _scrape_event_page(url: str, fallback_name: str) -> list[dict]:
    html = base.get(url)
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    name = (h1.get_text(" ", strip=True) if h1 else "") or fallback_name

    blocks = _content_blocks(soup)
    body_text = " ".join(text for _, text in blocks)

    description = _meta_description(soup, fallback=body_text)

    date_text = _extract_section(blocks, _DATE_LABELS)
    time_text = _extract_section(blocks, _TIME_LABELS)
    location_text = _extract_section(blocks, _LOCATION_LABELS)
    cost_text = _extract_section(blocks, _COST_LABELS)

    has_ticket_cta = bool(_TICKET_CTA_RE.search(body_text))
    cost_type, cost_label = _parse_cost(cost_text, has_ticket_cta)

    age = _extract_age(body_text)

    venue = location_text or "Smithsonian's National Zoo"
    place = "indoor" if _looks_indoor(location_text) else "outdoor"

    instances = _parse_date_instances(date_text, time_text)
    if not instances:
        return []

    events: list[dict] = []
    for start_dt, end_dt in instances:
        events.append(
            {
                "name": name,
                "start": start_dt,
                "end": end_dt,
                "venue": venue,
                "description": description,
                "url": url,
                "cost_type": cost_type,
                "cost_label": cost_label,
                "age": age,
                "venue_key": ID,
                "place": place,
                "source": ID,
            }
        )
    return events


# --------------------------------------------------------------------------
# Field parsing helpers
# --------------------------------------------------------------------------


def _meta_description(soup: BeautifulSoup, fallback: str = "") -> str:
    tag = soup.find("meta", attrs={"property": "og:description"}) or soup.find(
        "meta", attrs={"name": "description"}
    )
    text = (tag.get("content") or "").strip() if tag else ""
    if not text:
        text = (fallback or "").strip()
    if not text:
        return ""

    # The site's meta descriptions sometimes concatenate sentences with no
    # space ("...surprises.Throughout the Zoo..."), so split on a
    # sentence-end punctuation mark optionally followed by whitespace and
    # then a capital letter, rather than relying on whitespace alone.
    sentences = re.split(r"(?<=[.!?])\s*(?=[A-Z])", text)
    out = ""
    for sentence in sentences:
        out = f"{out} {sentence}".strip() if out else sentence
        if len(out) >= 180:
            break
    return out.strip()


def _parse_cost(cost_text: str, has_ticket_cta: bool) -> tuple[str, str]:
    text = (cost_text or "").strip()
    low = text.lower()

    if "$" in text or re.search(r"\bfee\b", low):
        return "paid", text
    if "free" in low:
        return ("free", "Free" if low == "free" else text)
    if text:
        # Some non-empty, non-"$"/"free" cost text (e.g. "Included with Zoo
        # admission"); trust a ticket-purchase CTA as a paid signal.
        return ("paid" if has_ticket_cta else "free"), text
    if has_ticket_cta:
        return "paid", "Tickets required (see event page)"
    return "free", ""


def _extract_age(text: str) -> str:
    for pattern in _AGE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0).strip()
    return ""


def _looks_indoor(location_text: str) -> bool:
    low = (location_text or "").lower()
    return any(keyword in low for keyword in _INDOOR_KEYWORDS)


# --------------------------------------------------------------------------
# Date / time parsing
# --------------------------------------------------------------------------


def _clean_date_fragment(text: str) -> str:
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("a.m.", "am").replace("p.m.", "pm")
    text = text.replace("A.M.", "AM").replace("P.M.", "PM")
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _safe_parse(text: str, default: datetime | None = None) -> datetime | None:
    text = (text or "").strip().strip(",")
    if not text:
        return None
    try:
        if default is not None:
            return dateparser.parse(text, fuzzy=True, default=default)
        return dateparser.parse(text, fuzzy=True)
    except (ValueError, OverflowError, TypeError):
        return None


def _parse_date_span(
    text: str,
) -> tuple[datetime | None, datetime | None]:
    """Parse a single date or an 'A - B' date range into (start, end)."""
    text = _clean_date_fragment(text)
    if not text:
        return None, None

    if "-" in text:
        left, right = text.split("-", 1)
        left, right = left.strip(), right.strip()

        left_guess = _safe_parse(left)

        # A bare "DD, YYYY" fragment (no month name of its own, e.g. the
        # "9, 2026" half of "Aug 7 - 9, 2026" or the "18, 2026" half of
        # "October 16-18, 2026") trips up dateutil's day/month heuristics --
        # it can read "18" as an invalid month rather than a day. Borrow the
        # month name from the other side of the range so parsing is
        # unambiguous instead of relying on dateutil's `default=`.
        right_for_parse = right
        if left_guess is not None and not _has_month_name(right):
            right_for_parse = f"{left_guess.strftime('%B')} {right}"

        end_dt = (
            _safe_parse(right_for_parse, default=left_guess)
            if left_guess is not None
            else _safe_parse(right_for_parse)
        )
        if end_dt is None:
            end_dt = _safe_parse(right)

        left_for_parse = left
        if end_dt is not None and not _has_month_name(left):
            left_for_parse = f"{end_dt.strftime('%B')} {left}"

        start_dt = (
            _safe_parse(left_for_parse, default=end_dt)
            if end_dt is not None
            else left_guess
        )

        if start_dt or end_dt:
            if start_dt and not end_dt:
                end_dt = start_dt
            if end_dt and not start_dt:
                start_dt = end_dt
            return start_dt, end_dt

    return _safe_parse(text), None


def _parse_time_span(text: str) -> tuple:
    """Parse the first one or two clock-time tokens found in `text` into
    (start_time, end_time). Only looks at the first two tokens so that
    trailing notes ("Zoo members get early access at 5 p.m.") appended to a
    time section don't get mistaken for the event's own end time."""
    text = _clean_date_fragment(text)
    if not text:
        return None, None
    tokens = _TIME_TOKEN_RE.findall(text)
    if not tokens:
        return None, None
    start_dt = _safe_parse(tokens[0])
    end_dt = (
        _safe_parse(tokens[1], default=start_dt)
        if len(tokens) > 1 and start_dt is not None
        else None
    )
    return (
        start_dt.time() if start_dt else None,
        end_dt.time() if end_dt else None,
    )


def _split_multi_dates(text: str) -> list[str]:
    """Detect a comma-separated list of distinct dates (e.g. multiple
    session dates for one program), as opposed to a single formatted date
    or an "A - B" range, and split it into individual date strings."""
    normalized = text.replace("\u2013", "-").replace("\u2014", "-")
    if "-" in normalized:
        return [text]

    if len(_MONTH_DAY_RE.findall(text)) < 2:
        return [text]

    parts = [p.strip() for p in text.split(",")]
    dates: list[str] = []
    buf = ""
    for part in parts:
        buf = f"{buf}, {part}".strip(", ") if buf else part
        starts_new_month = bool(re.match(r"^" + _MONTH_RE, part, re.I))
        has_year = bool(_YEAR_RE.search(part))
        if (has_year or starts_new_month) and buf != part:
            dates.append(buf)
            buf = ""
    if buf:
        dates.append(buf)
    return dates or [text]


def _parse_date_instances(
    date_text: str, time_text: str
) -> list[tuple[datetime, datetime | None]]:
    date_text = (date_text or "").strip()
    if not date_text:
        return []

    start_time, end_time = (None, None)
    if time_text:
        start_time, end_time = _parse_time_span(time_text)

    fragments = _split_multi_dates(date_text)
    instances: list[tuple[datetime, datetime | None]] = []

    for fragment in fragments:
        start_dt, end_dt = _parse_date_span(fragment)
        if not start_dt:
            continue

        if start_time:
            start_dt = start_dt.replace(
                hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0
            )

        if end_dt:
            if end_time:
                end_dt = end_dt.replace(
                    hour=end_time.hour, minute=end_time.minute, second=0, microsecond=0
                )
        elif end_time:
            end_dt = start_dt.replace(
                hour=end_time.hour, minute=end_time.minute, second=0, microsecond=0
            )

        instances.append((start_dt, end_dt))

    return instances
