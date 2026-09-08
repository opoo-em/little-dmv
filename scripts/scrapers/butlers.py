"""
Scraper for Butler's Orchard's seasonal Family Fun Day festivals.

Site reality check (as of this writing): the URL in this module's public contract,
https://butlersorchard.com/events/, redirects to
https://www.butlersorchard.com/visit-the-farm/events-calendar/. That page is a
WordPress (WPBakery) site whose event list is a "Modern Events Calendar"-style
widget that renders entirely client-side via AJAX. The server-rendered HTML for
that page contains no event markup at all -- it literally says "No event found!"
regardless of month/view -- so there is nothing for requests+BeautifulSoup to
parse there. That's also why a prior JSON-LD attempt found 0 events: there's no
data server-side to embed structured data around in the first place.

The real seasonal content -- Bunnyland, Spring Festival, Strawberry Festival,
Sunflower Spectacular, and the Pumpkin Festival -- lives on separate, ordinary
server-rendered WPBakery pages linked from the "Festivals + Farm Events" nav menu.
That nav menu IS present in the static HTML of the events page (it's part of the
site theme, not the AJAX widget), so fetch() uses it to discover the festival
pages, then parses each festival page's own "Dates" / "Hours" / "Admission" text.

Because the festival pages don't share one rigid template (some put date/hour
values in a separate paragraph below a "Dates:"/"Hours:" heading, one page puts
them inline after the label on the same line), parsing works off the page's
block-level text in document order rather than fixed CSS selectors, and looks
ahead to the next block when a label has no inline content of its own.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from datetime import time as dtime
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

from . import base

ID = "butlers-orchard"
NAME = "Butler's Orchard"
URL = "https://butlersorchard.com/events/"

_VENUE_KEY = "butlers-orchard"
_DEFAULT_VENUE = "Butler's Orchard"
_SITE_ROOT = "https://www.butlersorchard.com/"

# Known festival page paths. Used as a resilience fallback (matched anywhere on
# the page) in case the "Festivals + Farm Events" nav container can't be found
# or its markup changes shape -- and as the primary source of truth for which
# pages represent real, ticketed seasonal events.
_KNOWN_FESTIVAL_SLUGS = (
    "/festivals/bunnyland/",
    "/festivals/blossom-festival/",
    "/festivals/75th-anniversary/",
    "/visit-the-farm/sunflower-spectacular/",
    "/festivals/pumpkin-festival/",
)

_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
_MONTH_NAME_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))
_WEEKDAY_RE = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"

_TIME_RANGE_RE = re.compile(
    r"(\d{1,2})(?::(\d{2}))?\s*([APap])\.?[Mm]\.?\s*(?:-|–|—|to)\s*"
    r"(\d{1,2})(?::(\d{2}))?\s*([APap])\.?[Mm]\.?"
)
_PRICE_RE = re.compile(
    r"\$[\d,]+(?:\.\d{2})?(?:\s*[-–]\s*\$?[\d,]+(?:\.\d{2})?)?(?:/\w+)?"
)
_AGE_RE = re.compile(r"[Uu]nder\s+\d+\s*(?:months?|years?)[^.$]{0,40}")


def fetch() -> list[dict]:
    events: list[dict] = []

    html = base.get(URL)
    soup = BeautifulSoup(html, "html.parser")

    for page_url in _discover_festival_urls(soup):
        try:
            page_html = base.get(page_url)
        except Exception:
            # Network hiccup on one festival page shouldn't kill the whole scrape.
            continue
        try:
            events.extend(_parse_festival_page(page_html, page_url))
        except Exception:
            # Defensive: a single page's markup drifting shouldn't kill the rest.
            continue

    today = date.today()
    events = [e for e in events if (e["end"] or e["start"]).date() >= today]
    return events


# --------------------------------------------------------------------------- #
# Discovery: find the festival sub-pages from the events page's nav menu
# --------------------------------------------------------------------------- #

def _discover_festival_urls(soup: BeautifulSoup) -> list[str]:
    urls: dict[str, None] = {}  # insertion-ordered set

    nav_link = soup.find("a", string=re.compile(r"Festivals\s*\+\s*Farm Events", re.I))
    if nav_link is not None:
        container = nav_link.find_parent("li") or nav_link.find_parent()
        if container is not None:
            for a in container.find_all("a", href=True):
                if a is nav_link:
                    continue
                urls[urljoin(_SITE_ROOT, a["href"])] = None

    # Fallback / supplement: match known festival slugs anywhere on the page,
    # so discovery still works even if the nav container above can't be found.
    for a in soup.find_all("a", href=True):
        href = a["href"]
        for slug in _KNOWN_FESTIVAL_SLUGS:
            if slug in href:
                urls[urljoin(_SITE_ROOT, href)] = None

    return list(urls.keys())


# --------------------------------------------------------------------------- #
# Per-festival-page parsing
# --------------------------------------------------------------------------- #

def _content_blocks(soup: BeautifulSoup) -> list[str]:
    """Block-level text (h1-h6/p/li) restricted to the main content area,
    i.e. from the page's <h1> down to the footer ("Contact Us"). This skips
    the repeated header/nav markup (which also contains h1-h6/p/li elements)
    that would otherwise pollute the front of the block list."""
    tags = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"])
    texts = [t.get_text(" ", strip=True) for t in tags]

    h1_idx = next((i for i, t in enumerate(tags) if t.name == "h1" and texts[i]), None)
    if h1_idx is None:
        return []

    end_idx = len(texts)
    for i in range(h1_idx + 1, len(texts)):
        low = texts[i].strip().lower()
        if low == "contact us" or low.startswith("copyright"):
            end_idx = i
            break

    return [t for t in texts[h1_idx:end_idx] if t]


def _find_section(blocks: list[str], label: str) -> tuple[int, str]:
    """Find a "Label:" marker and return (block_index, text). Handles both
    "Label:" as its own heading (content is the next non-empty block) and
    "Label: content" inline in the same block."""
    pattern = re.compile(rf"\b{label}\b\s*:", re.I)
    for i, b in enumerate(blocks):
        m = pattern.search(b)
        if not m:
            continue
        after = b[m.end():].strip(" :-")
        if after:
            return i, after
        for j in range(i + 1, min(i + 3, len(blocks))):
            if blocks[j].strip():
                return j, blocks[j]
        return i, ""
    return -1, ""


def _find_hours_text(blocks: list[str]) -> str:
    """Like _find_section(blocks, "Hours"), but some pages (Pumpkin Festival)
    split hours across multiple lines by weekday group ("Wed-Fri: 1-6pm" /
    "Sat-Sun: 9am-6pm"). Keep pulling in following blocks as long as they
    look like more time ranges, so the fuller open/close span is captured."""
    pattern = re.compile(r"\bHours\b\s*:", re.I)
    for i, b in enumerate(blocks):
        m = pattern.search(b)
        if not m:
            continue
        after = b[m.end():].strip(" :-")
        parts = [after] if after else []
        j = i + 1
        while j < len(blocks) and len(parts) < 4:
            if _TIME_RANGE_RE.search(blocks[j]):
                parts.append(blocks[j])
                j += 1
                continue
            if not parts:
                parts.append(blocks[j])
                j += 1
            break
        return " ".join(p for p in parts if p)
    return ""


def _find_year(blocks: list[str]) -> int:
    text = " ".join(blocks)
    m = re.search(r"\b(20\d{2})\b", text)
    return int(m.group(1)) if m else date.today().year


def _parse_month_day(text: str, year: int) -> date | None:
    m = re.search(rf"({_MONTH_NAME_RE})\s+(\d{{1,2}})", text, re.I)
    if m:
        month = _MONTHS[m.group(1).lower()]
        try:
            return date(year, month, int(m.group(2)))
        except ValueError:
            return None
    # Fallback for month/day phrasing our own regex doesn't anticipate.
    try:
        return dateutil_parser.parse(f"{text} {year}", fuzzy=True).date()
    except (ValueError, OverflowError):
        return None


def _parse_date_ranges(dates_text: str, year_hint: int) -> list[tuple[date, date]]:
    text = dates_text
    text = re.sub(r"\([^)]*\)", "", text)  # drop parentheticals, e.g. "(closed Monday)"

    # Some pages (e.g. Bunnyland) run an exception aside ("Closed Easter
    # Sunday, April 5 / Open Easter Monday, April 6") into the very same text
    # block as the date list, with no separating punctuation. Those asides
    # start a new sentence with a capitalized annotation word; drop anything
    # from that point on rather than misreading it as more list items.
    m = re.search(r"\b(?:Closed|Open|Note|Please)\b", text)
    if m and m.start() > 0:
        text = text[: m.start()]

    text = re.sub(rf"\b{_WEEKDAY_RE}\b,?\s*", "", text, flags=re.I)

    year = year_hint
    m = re.search(r",?\s*\b(20\d{2})\b", text)
    if m:
        year = int(m.group(1))
        text = text[: m.start()] + text[m.end():]

    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\bthrough\b", "-", text, flags=re.I)
    text = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", text, flags=re.I)
    text = text.strip(" ,-")
    if not text:
        return []

    # Case 1: a single continuous "Month D - Month D" span (Pumpkin Festival,
    # Sunflower Spectacular): exactly one hyphen, a month name on each side.
    hyphen_parts = [p.strip() for p in text.split("-") if p.strip()]
    if len(hyphen_parts) == 2 and all(
        re.search(_MONTH_NAME_RE, p, re.I) for p in hyphen_parts
    ):
        start_d = _parse_month_day(hyphen_parts[0], year)
        end_d = _parse_month_day(hyphen_parts[1], year)
        if start_d and end_d:
            if end_d < start_d:
                end_d = _parse_month_day(hyphen_parts[1], year + 1)
            if start_d and end_d:
                return [(start_d, end_d)]

    # Case 2: an enumerated list of dates/short ranges (Bunnyland: "March
    # 28-29, April 2-4, 6, 11-12"; Spring Festival: "April 18, 25 and 26";
    # Strawberry Festival: "June 6 & June 7"). Bare numbers reuse the last
    # month named before them.
    text = re.sub(r"\band\b", ",", text, flags=re.I)
    tokens = [t.strip() for t in re.split(r"[,&]", text) if t.strip()]

    ranges: list[tuple[date, date]] = []
    current_month = None
    for tok in tokens:
        month_match = re.search(_MONTH_NAME_RE, tok, re.I)
        if month_match:
            current_month = _MONTHS[month_match.group(0).lower()]
            day_part = tok[month_match.end():]
        else:
            day_part = tok
        if current_month is None:
            continue
        day_nums = re.findall(r"\d{1,2}", day_part)
        if not day_nums:
            continue
        try:
            start_d = date(year, current_month, int(day_nums[0]))
            end_d = date(year, current_month, int(day_nums[-1]))
        except ValueError:
            continue
        ranges.append((start_d, end_d))
    return ranges


def _to_time(hour: str, minute: str, ampm: str) -> dtime:
    h = int(hour) % 12
    if ampm.lower() == "p":
        h += 12
    return dtime(h, int(minute) if minute else 0)


def _parse_hours(hours_text: str) -> tuple[dtime, dtime]:
    matches = _TIME_RANGE_RE.findall(hours_text)
    if not matches:
        return dtime(9, 0), dtime(18, 0)
    opens = [_to_time(h1, m1, ap1) for h1, m1, ap1, _, _, _ in matches]
    closes = [_to_time(h2, m2, ap2) for _, _, _, h2, m2, ap2 in matches]
    return min(opens), max(closes)


def _find_description(blocks: list[str], dates_idx: int) -> str:
    limit = dates_idx if dates_idx > 0 else len(blocks)
    for b in blocks[1:limit]:
        if len(b) >= 15 and ":" not in b[:10]:
            return b
    return ""


def _find_price(blocks: list[str]) -> tuple[str, str]:
    snippets = []
    for i, b in enumerate(blocks):
        if "$" not in b or len(b) > 200:
            continue
        prefix = ""
        prev = blocks[i - 1] if i > 0 else ""
        if prev and len(prev) < 40 and not any(ch.isdigit() for ch in prev):
            prefix = prev + " "
        snippet = (prefix + b).strip()
        if snippet not in snippets:
            snippets.append(snippet)
        if len(snippets) >= 2:
            break
    if not snippets:
        return "paid", "See event page"
    label = "; ".join(snippets)
    if len(label) > 160:
        label = label[:157] + "..."
    return "paid", label


def _find_age(blocks: list[str]) -> str:
    for b in blocks:
        low = b.lower()
        if "under" in low and "free" in low:
            m = _AGE_RE.search(b)
            if m:
                return m.group(0).strip(" *")
    return ""


def _parse_festival_page(html: str, page_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    blocks = _content_blocks(soup)
    if not blocks:
        return []

    name = blocks[0]

    dates_idx, dates_text = _find_section(blocks, "Dates")
    if not dates_text:
        return []
    hours_text = _find_hours_text(blocks)

    year_hint = _find_year(blocks[: max(dates_idx + 3, 6)])
    date_ranges = _parse_date_ranges(dates_text, year_hint)
    if not date_ranges:
        return []

    open_t, close_t = _parse_hours(hours_text) if hours_text else (dtime(9, 0), dtime(18, 0))
    description = _find_description(blocks, dates_idx)
    cost_type, cost_label = _find_price(blocks)
    age = _find_age(blocks)

    events = []
    for start_d, end_d in date_ranges:
        events.append({
            "name": name,
            "start": datetime.combine(start_d, open_t),
            "end": datetime.combine(end_d, close_t),
            "venue": _DEFAULT_VENUE,
            "description": description,
            "url": page_url,
            "cost_type": cost_type,
            "cost_label": cost_label,
            "age": age,
            "venue_key": _VENUE_KEY,
            "place": "outdoor",
            "source": ID,
        })
    return events
