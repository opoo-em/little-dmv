"""Scraper for The Puppet Co's Tiny Tots show schedule.

DATA SOURCE NOTES (read before "fixing" this):

The page at ``https://thepuppetco.org/tiny-tots`` (the URL below) is a
Squarespace marketing page. It has no Schema.org JSON-LD and no performance
dates anywhere in its HTML -- every "see the schedule" link just points at
the box office's ticketing platform, https://thepuppetco.showare.com, whose
calendar widgets are rendered client-side by JavaScript (the raw HTML is
"Loading..." placeholders). Neither page yields a schedule to a plain
requests+BeautifulSoup fetch.

The one place real, server-rendered performance dates exist is the
individual per-artist ticketing pages on that platform, e.g.:

    https://thepuppetco.showare.com/eventperformances.asp?evt=51

These are static HTML (confirmed via direct fetch) and list each show's
title, description, standard start time ("always at 10am!"), and upcoming
dates. There is, however, no crawlable index of which ``evt=`` ids are
currently active -- the ticketing site's own "upcoming events" listing is
also JS-rendered. The ARTIST_EVT_IDS mapping below was found by hand
(matching artist names on /tiny-tots to indexed showare.com pages) and is
the main maintenance liability in this file: if Puppet Co. adds a new
guest artist, this scraper will not discover their evt= id on its own.
It *will* correctly drop an artist that's no longer listed on /tiny-tots,
since we only fetch evt pages for artists whose name still appears there.

fetch() therefore does the following:
  1. GET the Tiny Tots page. Check for JSON-LD Event nodes (future-proofing
     -- there are none today, but if Squarespace/Puppet Co. ever adds
     structured data this will pick it up and skip the fallback).
  2. Otherwise, read which guest-artist sections are currently listed on
     that page, look up each one's showare.com evt= id, and parse the
     per-artist ticketing page for titles/times/dates.

The per-artist pages are hand-entered CMS content, not a fixed template --
date formats vary ("Sunday, August 23rd" vs "Wed, Nov 19"), and show
titles/times are sometimes on their own line and sometimes run together
with the surrounding description with no separating whitespace at all.
The parser below works off text anchored between two boilerplate phrases
that were consistent across every sample page ("Part of our Tiny Tots
Series" ... "Questions? Call the box office."), scanning for an
"always at <time>" trigger to close out each show block rather than
assuming a rigid line structure.
"""

import re
from datetime import date, datetime, timedelta

from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

from . import base

ID = "puppetco-tinytots"
NAME = "The Puppet Co — Tiny Tots"
URL = "https://thepuppetco.org/tiny-tots"

VENUE_NAME = "The Puppet Co at Glen Echo Park"
AGE_RANGE = "18 months - 4 years"

SHOWARE_EVT_URL = "https://thepuppetco.showare.com/eventperformances.asp?evt={evt_id}"

# Guest-artist name (normalized) -> showare.com evt= id for their Tiny Tots
# ticketing page. See module docstring for why this has to be hardcoded.
ARTIST_EVT_IDS = {
    "ingrid mollie": 18,       # "Tiny Tots starring TPC's Favorite Faces"
    "beale street puppets": 39,
    "beech tree puppets": 12,
    "happy theater": 51,
    "pennys puppets": 8,       # "Tiny Tots starring Penny Russell"
}

TITLE_BLOCKLIST = {"starring", "information", "questions", "tickets", "ticket price"}

# Boilerplate that shows up after the last show's dates but before the
# "Questions? Call the box office." end-of-content marker. We cut the
# content window at whichever of these appears earliest, so none of it
# gets swept up into a date list or a description.
STOP_MARKERS = (
    "looking for another date",
    "ticket price",
    "tickets required",
    "more dates and titles coming soon",
    "please help us",
)

WEEKDAY_RE = (
    r"(?:Sun(?:day)?|Mon(?:day)?|Tue(?:s|sday)?|Wed(?:nesday)?"
    r"|Thu(?:r|rs|rsday)?|Fri(?:day)?|Sat(?:urday)?)"
)
MONTH_RE = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
DATE_RE = re.compile(
    rf"\b{WEEKDAY_RE}\.?,?\s+(?P<month>{MONTH_RE})\.?\s+(?P<day>\d{{1,2}})(?:st|nd|rd|th)?\b",
    re.IGNORECASE,
)
TIME_RE = re.compile(
    r"always\s+at\s+(?P<time>\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)", re.IGNORECASE
)
# Not line-anchored: applied within an arbitrary slice of the flattened,
# whitespace-normalized page text (see _title_and_desc_from_block).
COLON_TITLE_RE = re.compile(r"([A-Z][A-Za-z0-9'’&!?() \-]{1,70}):")

# The only performer names observed in "with <name>" date annotations on
# these pages. Kept as an allowlist (rather than a generic capitalized-word
# grab) because a show title can itself be capitalized words right after a
# date (e.g. "... Jennie Gives a Gift"), which would otherwise be swallowed
# as a bogus "suffix". Extend this if the box office adds another regular
# performer.
KNOWN_PERFORMER_NAMES = ("Ingrid and Mollie", "Mollie and Ingrid", "Ingrid", "Mollie")
SUFFIX_RE = re.compile(
    r"^[\s,]*with\s+(" + "|".join(re.escape(n) for n in KNOWN_PERFORMER_NAMES) + r")\b",
    re.IGNORECASE,
)

MONTH_NUM = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def fetch() -> list[dict]:
    now = datetime.now()
    html = base.get(URL)
    soup = BeautifulSoup(html, "html.parser")

    jsonld_events = _events_from_jsonld(soup, now)
    if jsonld_events:
        return sorted(jsonld_events, key=lambda e: e["start"])

    events = []
    for key in _current_artist_keys(soup):
        evt_id = ARTIST_EVT_IDS.get(key)
        if evt_id is None:
            continue
        evt_url = SHOWARE_EVT_URL.format(evt_id=evt_id)
        try:
            evt_html = base.get(evt_url)
        except Exception:
            continue
        events.extend(_parse_evt_page(evt_html, evt_url, now))

    return sorted(events, key=lambda e: e["start"])


# --- JSON-LD path (defensive; no JSON-LD found on the page as of writing) ---

def _events_from_jsonld(soup, now):
    nodes = []
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            data = __import__("json").loads(raw)
        except ValueError:
            continue
        nodes.extend(_extract_event_nodes(data))

    events = []
    for node in nodes:
        d = _jsonld_event_to_dict(node, now)
        if d:
            events.append(d)
    return events


def _extract_event_nodes(node):
    found = []
    if isinstance(node, dict):
        types = node.get("@type")
        types = [types] if isinstance(types, str) else (types or [])
        if any(isinstance(t, str) and t.lower() == "event" for t in types):
            found.append(node)
        for value in node.values():
            found.extend(_extract_event_nodes(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_extract_event_nodes(item))
    return found


def _jsonld_event_to_dict(node, now):
    name = node.get("name")
    start_raw = node.get("startDate")
    if not name or not start_raw:
        return None
    try:
        start = dateutil_parser.parse(start_raw)
    except (ValueError, TypeError):
        return None
    if start.tzinfo is not None:
        start = start.replace(tzinfo=None)
    if start < now:
        return None

    end = None
    end_raw = node.get("endDate")
    if end_raw:
        try:
            end = dateutil_parser.parse(end_raw)
            if end.tzinfo is not None:
                end = end.replace(tzinfo=None)
        except (ValueError, TypeError):
            end = None
    if end is None:
        end = start + timedelta(minutes=30)

    price = None
    offers = node.get("offers")
    if isinstance(offers, dict):
        price = offers.get("price")
    elif isinstance(offers, list) and offers and isinstance(offers[0], dict):
        price = offers[0].get("price")
    cost_label = f"${price} per person" if price else "See ticketing page"

    return {
        "name": name,
        "start": start,
        "end": end,
        "venue": VENUE_NAME,
        "description": node.get("description", "") or "",
        "url": node.get("url", URL),
        "cost_type": "paid",
        "cost_label": cost_label,
        "age": AGE_RANGE,
        "venue_key": ID,
        "place": "indoor",
        "source": ID,
    }


# --- HTML fallback (the path actually used today) ---

def _normalize_artist(text):
    t = text.strip().lower()
    t = re.sub(r"^guest artist:\s*", "", t)
    t = re.sub(r"[^a-z0-9 ]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _current_artist_keys(soup):
    keys = []
    for tag in soup.find_all(re.compile(r"^h[1-6]$")):
        key = _normalize_artist(tag.get_text(" ", strip=True))
        if key in ARTIST_EVT_IDS and key not in keys:
            keys.append(key)
    return keys


def _series_title_from_soup(soup):
    if soup.title:
        text = soup.title.get_text()
        parts = [p.strip() for p in text.split("|")]
        if len(parts) >= 2:
            return parts[1]
        if parts:
            return parts[0]
    return "Tiny Tots"


def _parse_time(t):
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?", t.strip(), re.IGNORECASE)
    if not m:
        raise ValueError(f"unrecognized time: {t!r}")
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm = m.group(3).lower()
    if ampm == "p" and hour != 12:
        hour += 12
    if ampm == "a" and hour == 12:
        hour = 0
    return hour, minute


def _resolve_year(month, day, now):
    """Assume current year; roll to next year only for an early-in-the-year
    date (Jan-Apr) being read late in the current year (Oct-Dec), which is
    the one case where a same-year interpretation would wrongly look past.
    Anything else that lands in the past is left alone and filtered out by
    the "skip past performances" check in _parse_evt_page.
    """
    candidate = date(now.year, month, day)
    if candidate < now.date() and now.month >= 10 and month <= 4:
        candidate = date(now.year + 1, month, day)
    return candidate


def _title_and_desc_from_block(block_text):
    """Given the free text that leads up to (but doesn't include) an
    "always at <time>" trigger, work out the show title and description.

    Returns (title_or_None, description, leading_text_before_any_title) --
    the third item is what should be treated as company/series-level blurb
    if this is the first block in the page.
    """
    block_text = block_text.strip(" ,.-")
    if not block_text:
        return None, "", ""

    # Prefer an explicit "Show Title:" style marker -- take the LAST one in
    # the block, since an earlier one (rare) would belong to a previous show.
    for cm in reversed(list(COLON_TITLE_RE.finditer(block_text))):
        phrase = cm.group(1).strip()
        if phrase.lower() in TITLE_BLOCKLIST or "." in phrase:
            continue
        desc = block_text[cm.end():].strip(" ,.-")
        desc = re.sub(r"come see the show,?$", "", desc, flags=re.IGNORECASE).strip(" ,.-")
        blurb = block_text[:cm.start()].strip(" ,.-")
        return phrase, desc, blurb

    # No colon title. Titles that are inline with the time clause look like
    # "...previous sentence. Show Title, always at 10am!" or "...(Ask Box
    # Office...) Show Title, always at 10am!" -- take whatever follows the
    # last sentence/clause boundary, if it's short and starts with a letter
    # (so we don't grab a stray trailing ")" or similar punctuation).
    m = re.search(r"[.!?)]\s*([A-Za-z][A-Za-z0-9'’&,()\-\s]{2,69})$", block_text)
    if m:
        candidate = re.sub(
            r"^come see the show$", "", m.group(1).strip(" ,.-"), flags=re.IGNORECASE
        ).strip(" ,.-")
        if candidate and candidate.lower() not in TITLE_BLOCKLIST:
            return candidate, "", block_text[: m.start(1)].strip(" ,.-")

    # The whole block might just be a short standalone title with nothing
    # meaningful in front of it (e.g. the very first show on the page, or
    # a title that itself contains one "!" like "Jennie Gives a Gift (NEW
    # show!)"). Allow at most one ! or ? and no periods (real prose almost
    # always has a period or runs much longer than a title would).
    if (
        len(block_text) <= 80
        and block_text.count(".") == 0
        and (block_text.count("!") + block_text.count("?")) <= 1
    ):
        return block_text, "", ""

    return None, "", block_text


def _extract_dates_with_end(region):
    """Find every date in `region`, plus the character offset right after
    the last one -- so the caller can advance past consumed dates instead
    of re-reading them as leading text for the next show.
    """
    matches = list(DATE_RE.finditer(region))
    dates = []
    last_end = 0
    for dm in matches:
        tail = region[dm.end():dm.end() + 40]
        sm = SUFFIX_RE.match(tail)
        if sm:
            suffix = sm.group(1)
            last_end = dm.end() + sm.end()  # consume the matched "with <name>" too
        else:
            suffix = ""
            last_end = dm.end()
        dates.append({"month": dm.group("month"), "day": int(dm.group("day")), "suffix": suffix})
    return dates, last_end


def _parse_evt_page(html, evt_url, now):
    soup = BeautifulSoup(html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with(" ")
    text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()

    series_title = _series_title_from_soup(soup)

    start_m = re.search(r"part of our tiny tots series", text, re.IGNORECASE)
    end_m = re.search(r"questions\?\s*call the box office", text, re.IGNORECASE)
    if start_m and end_m and end_m.start() > start_m.end():
        content = text[start_m.end():end_m.start()]
    elif start_m:
        content = text[start_m.end():]
    else:
        content = text
    content = content.lstrip(" *").strip()

    price_m = re.search(
        r"ticket price:?\s*\$?([\d]+(?:\.\d{2})?)\s*per person", content, re.IGNORECASE
    )
    cost_label = f"${price_m.group(1)} per person" if price_m else "See ticketing page"

    # Everything from the earliest boilerplate stop-phrase onward isn't
    # show content (it's "looking for another date / ticket price / ..."
    # text), so trim the working window there.
    stop_pos = len(content)
    for marker in STOP_MARKERS:
        sm = re.search(re.escape(marker), content, re.IGNORECASE)
        if sm and sm.start() < stop_pos:
            stop_pos = sm.start()

    time_matches = [tm for tm in TIME_RE.finditer(content) if tm.start() < stop_pos]
    if not time_matches:
        return []

    events = []
    company_blurb = None
    cursor = 0
    for i, tm in enumerate(time_matches):
        lead_text = content[cursor:tm.start()]
        title, desc, blurb_piece = _title_and_desc_from_block(lead_text)
        if company_blurb is None:
            company_blurb = blurb_piece
        show_title = title or series_title
        show_desc = desc or company_blurb or ""

        next_boundary = time_matches[i + 1].start() if i + 1 < len(time_matches) else stop_pos
        date_region = content[tm.end():next_boundary]
        dates, last_date_end = _extract_dates_with_end(date_region)
        cursor = tm.end() + last_date_end

        if not dates:
            continue
        try:
            hour, minute = _parse_time(tm.group("time"))
        except ValueError:
            continue

        for d in dates:
            month = MONTH_NUM.get(d["month"][:3].lower())
            if not month:
                continue
            try:
                event_date = _resolve_year(month, d["day"], now)
            except ValueError:
                continue
            start = datetime(event_date.year, event_date.month, event_date.day, hour, minute)
            if start < now:
                continue
            end = start + timedelta(minutes=30)
            name = show_title
            if d["suffix"]:
                name = f"{name} ({d['suffix']})"
            events.append({
                "name": name,
                "start": start,
                "end": end,
                "venue": VENUE_NAME,
                "description": show_desc,
                "url": evt_url,
                "cost_type": "paid",
                "cost_label": cost_label,
                "age": AGE_RANGE,
                "venue_key": ID,
                "place": "indoor",
                "source": ID,
            })
    return events
