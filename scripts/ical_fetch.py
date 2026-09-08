"""Fetch and parse iCal feeds into raw event dicts.

Each raw dict conforms to the shape expected by normalize.to_canonical:
    { name, start, end, venue, description, url, source, ... }

We only surface events within the next LOOKAHEAD_DAYS. Recurring events (RRULE)
are expanded within the window using dateutil.rrule.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

import requests
from dateutil.rrule import rrulestr
from icalendar import Calendar

LOOKAHEAD_DAYS = 21
USER_AGENT = "little-dmv-bot/1.0 (+https://github.com/opoo-em/little-dmv)"


@dataclass
class ICalSource:
    id: str
    name: str
    url: str
    venue_default: str = ""
    place_default: str = "indoor"
    distance_venue_key: str | None = None
    source: str = "ical"


def fetch(source: ICalSource, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    horizon = now + timedelta(days=LOOKAHEAD_DAYS)

    resp = requests.get(source.url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    cal = Calendar.from_ical(resp.content)

    out: list[dict] = []
    for component in cal.walk("vevent"):
        for start in _expand(component, now, horizon):
            end = _event_end(component, start)
            out.append(_to_raw(component, start, end, source))
    return out


def _to_raw(component, start: datetime, end: datetime | None, source: ICalSource) -> dict:
    location = _ical_str(component.get("location")).strip()
    return {
        "name": _ical_str(component.get("summary")).strip(),
        "start": start,
        "end": end,
        "venue": location or source.venue_default,
        "description": _ical_str(component.get("description")).strip(),
        "url": _ical_str(component.get("url")).strip(),
        "source": source.source or source.id,
        "place": source.place_default,
        "venue_key": source.distance_venue_key,
        "age": _extract_age(component),
    }


_AGE_HINT_KEYS = ("categories", "description", "summary")


def _ical_str(val) -> str:
    """Coerce an icalendar value (vText, vCategory, list of same) to plain str.

    Bare str(val) on a vCategory returns the Python repr —
    `vCategory([vText(b'NZP Kids and Families')], params=Parameters({}))` —
    which then leaks into our output. Prefer .to_ical() and decode.
    """
    if val is None:
        return ""
    try:
        raw = val.to_ical()
    except AttributeError:
        return str(val)
    if isinstance(raw, bytes):
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("utf-8", errors="replace")
    return str(raw)


def _extract_age(component) -> str:
    parts = []
    for key in _AGE_HINT_KEYS:
        val = component.get(key)
        if not val:
            continue
        parts.append(_ical_str(val))
    return " | ".join(p for p in parts if p)


def _event_start(component) -> datetime | None:
    dt = component.get("dtstart")
    if dt is None:
        return None
    value = dt.dt
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)


def _event_end(component, start: datetime) -> datetime | None:
    dt = component.get("dtend")
    if dt is None:
        return None
    value = dt.dt
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=start.tzinfo or timezone.utc)
    return datetime(value.year, value.month, value.day, tzinfo=start.tzinfo or timezone.utc)


def _expand(component, now: datetime, horizon: datetime) -> Iterable[datetime]:
    start = _event_start(component)
    if start is None:
        return

    rrule_prop = component.get("rrule")
    if rrule_prop is None:
        if now <= start <= horizon:
            yield start
        return

    # Recurrence — expand within the window.
    rule_text = rrule_prop.to_ical().decode("utf-8")
    try:
        rule = rrulestr(rule_text, dtstart=start)
    except Exception:
        # Malformed rule — fall back to just the seed.
        if now <= start <= horizon:
            yield start
        return

    for occ in rule.between(now, horizon, inc=True):
        if occ.tzinfo is None:
            occ = occ.replace(tzinfo=start.tzinfo or timezone.utc)
        yield occ
