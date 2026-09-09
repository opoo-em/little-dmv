"""Scraper for National Children's Museum events.

nationalchildrensmuseum.org is a Next.js + Sanity site. The events listing
page (/explore/events) renders its cards client-side, so a plain HTTP GET of
that page usually returns an empty list section. Individual event pages
(/explore/events/<slug>) *are* server-rendered with a consistent structure
(h1 title, "about" description, "details" venue/age), but the per-event
schedule calendar's actual clickable dates also appear to be populated by
client-side JS.

Because of that, this module tries several strategies in order and quietly
falls back rather than guessing:

  1. Schema.org JSON-LD `Event` nodes, if the site ever emits them (checked
     on both the listing page and each detail page).
  2. Discovery of individual event URLs via <a href> links on the listing
     page and, as a backstop, sitemap.xml / sitemap index files.
  3. Structural HTML parsing of each detail page for name / description /
     venue / age (verified against the live "automata" event page).
  4. A cascade of heuristics to recover the actual date/time instances:
     <time> elements -> date-ish data-* attributes -> embedded JSON script
     blobs (e.g. a Next.js data payload) -> a conservative reader of the
     visible month calendar that only trusts day cells that look
     interactive (wrapped in <a>/<button> or carrying an "active"-style
     class), combined with a time-of-day guess pulled from nearby page text.

If none of the date heuristics find anything for a given event, that event
is simply skipped rather than fabricated. If the underlying markup changes
shape, step 4 is the piece most likely to need adjustment.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime

from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from . import base

ID = "national-childrens-museum"
NAME = "National Children's Museum"
URL = "https://nationalchildrensmuseum.org/explore/events"

_SITE_ROOT = "https://nationalchildrensmuseum.org"
DEFAULT_VENUE = NAME
DEFAULT_COST_LABEL = "Included with admission"

_EVENT_PATH_RE = re.compile(r"/explore/events/([a-z0-9][a-z0-9\-]*)/?$", re.I)
_ISO_DATE_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?\b"
)
_MONTH_YEAR_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+(\d{4})$",
    re.I,
)
_PRICE_RE = re.compile(r"\$\s?\d[\d,.]*")
_TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\s*([ap]\.?m\.?)\b", re.I)


def fetch() -> list[dict]:
    events: list[dict] = []

    try:
        listing_html = base.get(URL)
    except Exception:
        return events

    listing_soup = BeautifulSoup(listing_html, "html.parser")

    events.extend(_events_from_jsonld(listing_html, page_url=URL))

    seen_urls = {e["url"] for e in events if e.get("url")}
    for detail_url in _discover_event_urls(listing_soup):
        if detail_url in seen_urls:
            continue
        seen_urls.add(detail_url)
        try:
            detail_html = base.get(detail_url)
        except Exception:
            continue

        page_events = _events_from_jsonld(detail_html, page_url=detail_url)
        if not page_events:
            page_events = _parse_event_detail(detail_html, detail_url)
        events.extend(page_events)

    return _dedupe_and_filter_past(events)


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------

def _discover_event_urls(listing_soup: BeautifulSoup) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    def _add(href: str) -> None:
        cleaned = href.split("#")[0].split("?")[0]
        if not _EVENT_PATH_RE.search(cleaned):
            return
        full = urljoin(_SITE_ROOT, cleaned)
        key = full.rstrip("/")
        if key not in seen:
            seen.add(key)
            urls.append(full)

    for a in listing_soup.find_all("a", href=True):
        _add(a["href"])

    try:
        sitemap_xml = base.get(f"{_SITE_ROOT}/sitemap.xml")
    except Exception:
        sitemap_xml = ""

    if sitemap_xml:
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sitemap_xml)
        nested_sitemaps = [loc for loc in locs if loc.lower().endswith(".xml")]
        for loc in locs:
            _add(loc)
        for nested in nested_sitemaps[:5]:
            try:
                nested_xml = base.get(nested)
            except Exception:
                continue
            for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", nested_xml):
                _add(loc)

    return urls


# --------------------------------------------------------------------------
# JSON-LD path
# --------------------------------------------------------------------------

def _events_from_jsonld(html: str, page_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[dict] = []

    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = (tag.string or tag.get_text() or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue
        for node in _walk_jsonld_nodes(data):
            if not _is_event_node(node):
                continue
            event = _event_from_jsonld_node(node, page_url)
            if event:
                out.append(event)

    return out


def _walk_jsonld_nodes(data):
    if isinstance(data, list):
        for item in data:
            yield from _walk_jsonld_nodes(item)
    elif isinstance(data, dict):
        if isinstance(data.get("@graph"), list):
            for item in data["@graph"]:
                yield from _walk_jsonld_nodes(item)
        else:
            yield data


def _is_event_node(node: dict) -> bool:
    t = node.get("@type")
    if isinstance(t, str):
        return "event" in t.lower()
    if isinstance(t, list):
        return any(isinstance(x, str) and "event" in x.lower() for x in t)
    return False


def _event_from_jsonld_node(node: dict, page_url: str) -> dict | None:
    name = _text(node.get("name"))
    start = _parse_dt(node.get("startDate"))
    if not name or start is None:
        return None
    end = _parse_dt(node.get("endDate"))

    venue = DEFAULT_VENUE
    location = node.get("location")
    if isinstance(location, list) and location:
        location = location[0]
    if isinstance(location, dict):
        venue = _text(location.get("name")) or venue
    elif isinstance(location, str) and location.strip():
        venue = location.strip()

    description = _clean_text(_text(node.get("description")))

    event_url = _text(node.get("url")) or page_url
    event_url = urljoin(_SITE_ROOT, event_url)

    age = _text(node.get("typicalAgeRange"))
    if not age:
        audience = node.get("audience")
        if isinstance(audience, dict):
            age = _text(audience.get("suggestedMinAge"))

    cost_type, cost_label = _cost_from_offers(node.get("offers"))

    return {
        "name": name,
        "start": start,
        "end": end,
        "venue": venue,
        "description": description,
        "url": event_url,
        "cost_type": cost_type,
        "cost_label": cost_label,
        "age": age,
        "venue_key": ID,
        "place": "indoor",
        "source": ID,
    }


def _cost_from_offers(offers) -> tuple[str, str]:
    if isinstance(offers, dict):
        offers = [offers]
    if not isinstance(offers, list) or not offers:
        return "paid", DEFAULT_COST_LABEL

    parts: list[str] = []
    all_free = True
    any_price_found = False

    for offer in offers:
        if not isinstance(offer, dict):
            continue
        price = offer.get("price")
        try:
            price_val = float(price)
            any_price_found = True
        except (TypeError, ValueError):
            price_val = None

        label = _text(offer.get("name")) or _text(offer.get("description"))
        if price_val is not None:
            all_free = all_free and price_val == 0
            if not label:
                label = "Free" if price_val == 0 else f"${price_val:g}"
        if label:
            parts.append(label)

    if not any_price_found:
        return "paid", DEFAULT_COST_LABEL

    cost_type = "free" if all_free else "paid"
    cost_label = " / ".join(dict.fromkeys(parts)) if parts else DEFAULT_COST_LABEL
    return cost_type, cost_label


# --------------------------------------------------------------------------
# Per-site HTML fallback
# --------------------------------------------------------------------------

def _parse_event_detail(html: str, url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    if re.search(r"this event has expired", page_text, re.I):
        return []

    name = _detail_name(soup)
    if not name:
        return []

    description = _detail_description(soup)
    venue = _detail_icon_text(soup, "location icon") or DEFAULT_VENUE
    age = _detail_icon_text(soup, "ages icon")
    age = re.sub(r"(?i)^recommended ages:\s*", "", age).strip()

    cost_type, cost_label = _detail_cost(page_text)

    events: list[dict] = []
    for start, end in _detail_schedule_datetimes(soup):
        events.append({
            "name": name,
            "start": start,
            "end": end,
            "venue": venue,
            "description": description,
            "url": url,
            "cost_type": cost_type,
            "cost_label": cost_label,
            "age": age,
            "venue_key": ID,
            "place": "indoor",
            "source": ID,
        })
    return events


def _detail_name(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    if h1:
        text = _clean_text(h1.get_text(" ", strip=True))
        if text:
            return text
    meta = soup.find("meta", attrs={"property": "og:title"})
    if meta and meta.get("content"):
        return _clean_text(meta["content"].split("|")[0])
    if soup.title and soup.title.string:
        return _clean_text(soup.title.string.split("|")[0])
    return ""


def _detail_description(soup: BeautifulSoup) -> str:
    heading = soup.find(
        lambda tag: tag.name in ("h2", "h3", "h4")
        and tag.get_text(strip=True).lower() == "about"
    )
    if heading:
        parts = []
        for sib in heading.find_next_siblings():
            if sib.name in ("h2", "h3", "h4"):
                break
            text = sib.get_text(" ", strip=True)
            if text:
                parts.append(text)
        text = _clean_text(" ".join(parts))
        if text:
            return text

    meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", attrs={"property": "og:description"}
    )
    if meta and meta.get("content"):
        return _clean_text(meta["content"])
    return ""


def _detail_icon_text(soup: BeautifulSoup, alt_keyword: str) -> str:
    img = soup.find("img", alt=lambda a: a and alt_keyword.lower() in a.lower())
    if not img or not img.parent:
        return ""
    return _clean_text(img.parent.get_text(" ", strip=True))


def _detail_cost(page_text: str) -> tuple[str, str]:
    sentences = re.split(r"(?<=[.!?])\s+", page_text)

    price_sentence = next((s for s in sentences if _PRICE_RE.search(s)), None)
    if price_sentence:
        return "paid", _clean_text(price_sentence)[:200]

    free_sentence = next((s for s in sentences if re.search(r"\bfree\b", s, re.I)), None)
    if free_sentence:
        return "free", _clean_text(free_sentence)[:200]

    return "paid", DEFAULT_COST_LABEL


def _detail_schedule_datetimes(soup: BeautifulSoup) -> list[tuple[datetime, datetime | None]]:
    results: list[tuple[datetime, datetime | None]] = []

    for t in soup.find_all("time"):
        dt = _parse_dt(t.get("datetime") or t.get_text(strip=True))
        if dt:
            results.append((dt, None))
    if results:
        return _dedupe_datetimes(results)

    for tag in soup.find_all(True):
        for attr, value in tag.attrs.items():
            if not isinstance(value, str):
                continue
            attr_l = attr.lower()
            if "date" in attr_l or attr_l in ("data-start", "data-time"):
                dt = _parse_dt(value)
                if dt:
                    results.append((dt, None))
    if results:
        return _dedupe_datetimes(results)

    for script in soup.find_all("script"):
        script_type = (script.get("type") or "").lower()
        script_id = (script.get("id") or "").lower()
        looks_like_data_blob = (
            script_type == "application/json"
            or "next_data" in script_id
            or "nuxt" in script_id
        )
        if not looks_like_data_blob:
            continue
        raw = script.string or script.get_text() or ""
        for match in _ISO_DATE_RE.findall(raw):
            dt = _parse_dt(match)
            if dt:
                results.append((dt, None))
    if results:
        return _dedupe_datetimes(results)

    return _calendar_table_fallback(soup)


def _calendar_table_fallback(soup: BeautifulSoup) -> list[tuple[datetime, datetime | None]]:
    month_heading = soup.find(
        lambda tag: tag.name in ("h2", "h3", "h4", "p", "span", "div", "button")
        and tag.get_text(strip=True)
        and _MONTH_YEAR_RE.match(tag.get_text(strip=True))
    )
    if month_heading is None:
        return []

    m = _MONTH_YEAR_RE.match(month_heading.get_text(strip=True))
    month_num = datetime.strptime(m.group(1), "%B").month
    year = int(m.group(2))

    schedule_section = month_heading.find_parent(["section", "div"]) or soup
    time_hint = _detail_time_hint(soup)

    results: list[tuple[datetime, datetime | None]] = []
    for cell in schedule_section.find_all(["td", "button", "a", "div", "span"]):
        classes = " ".join(cell.get("class", [])).lower()
        if any(bad in classes for bad in ("disabled", "inactive", "empty", "outside", "past")):
            continue
        if cell.find(["td", "button", "a", "div", "span"]):
            continue  # not a leaf cell
        own_text = cell.get_text(strip=True)
        if not own_text.isdigit():
            continue
        is_interactive = (
            cell.name in ("button", "a")
            or cell.find(["a", "button"]) is not None
            or any(k in classes for k in ("active", "available", "event", "selected"))
        )
        if not is_interactive:
            continue
        try:
            naive_date = date(year, month_num, int(own_text))
        except ValueError:
            continue
        dt = datetime.combine(naive_date, time_hint or datetime.min.time())
        results.append((dt, None))

    return _dedupe_datetimes(results)


def _detail_time_hint(soup: BeautifulSoup):
    match = _TIME_RE.search(soup.get_text(" ", strip=True))
    if not match:
        return None
    hour, minute, meridiem = match.groups()
    hour, minute = int(hour), int(minute)
    meridiem = meridiem.lower().replace(".", "")
    if meridiem == "pm" and hour != 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    try:
        return datetime.min.time().replace(hour=hour, minute=minute)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Small utils
# --------------------------------------------------------------------------

def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list) and value:
        return _text(value[0])
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    try:
        return dateparser.parse(value)
    except (ValueError, OverflowError, TypeError):
        return None


def _dedupe_datetimes(pairs):
    seen = set()
    out = []
    for start, end in pairs:
        key = (start, end)
        if key in seen:
            continue
        seen.add(key)
        out.append((start, end))
    out.sort(key=lambda p: p[0])
    return out


def _dedupe_and_filter_past(events: list[dict]) -> list[dict]:
    now = datetime.now()
    today_start = datetime.combine(now.date(), datetime.min.time())

    seen = set()
    out = []
    for event in events:
        start = event.get("start")
        if not isinstance(start, datetime) or start < today_start:
            continue
        key = (event.get("name"), start, event.get("url"))
        if key in seen:
            continue
        seen.add(key)
        out.append(event)

    out.sort(key=lambda e: e["start"])
    return out
