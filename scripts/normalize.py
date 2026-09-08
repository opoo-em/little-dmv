"""Normalize raw events (from iCal or scrapers) into the canonical schema
defined in README.md.

Each raw event dict is expected to carry at least:
    - name: str
    - start: datetime (tz-aware or naive local)
    - url: str
    - source: str (pipeline id)

Optional fields:
    - end: datetime
    - venue: str
    - description: str
    - age: str (raw text — passed through the age filter)
    - place: 'indoor' | 'outdoor'
    - cost_type: 'free' | 'paid'
    - cost_label: str
    - lat, lng: float (overrides venue_key for distance)
    - venue_key: str (looked up in distance.VENUE_COORDS)
    - expires_at: datetime | None
"""

from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from . import distance
from .filter import age_passes, content_passes, looks_out_of_dmv

# All display date/time fields are rendered in DMV local time. iCal feeds
# arrive in a variety of timezones (some UTC, some TZID=America/New_York,
# some floating). Normalize the presentation so Em never sees a UTC time.
_LOCAL_TZ = ZoneInfo("America/New_York")


def _to_local(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_LOCAL_TZ)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_LITERAL_ESC_RE = re.compile(r"\\[nrt]")
# iCal (RFC 5545) escapes `,` `;` and `\` as `\,` `\;` `\\` in TEXT values.
# When we round-trip through icalendar's .to_ical(), these come back
# escaped. Undo them for display.
_ICAL_ESC_RE = re.compile(r"\\([,;\\])")


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "event"


def _clean_text(raw: str) -> str:
    """Decode HTML entities, strip tags, collapse whitespace.

    Handles double-encoded entities (e.g. `&amp;lt;p&amp;gt;`) by unescaping
    twice, and normalizes literal `\\n`/`\\t` sequences that show up when a
    source shoves an escaped string into a description field.
    """
    if not raw:
        return ""
    s = html.unescape(html.unescape(raw))
    s = _ICAL_ESC_RE.sub(r"\1", s)
    s = _LITERAL_ESC_RE.sub(" ", s)
    s = _TAG_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s)
    return s.strip()


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_id(source: str, name: str, start: datetime) -> str:
    base = f"{_slug(source)}-{_slug(name)}-{start.date().isoformat()}"
    if len(base) > 80:
        base = base[:80] + "-" + hashlib.sha1(base.encode()).hexdigest()[:8]
    return base


def to_canonical(raw: dict[str, Any], now: Optional[datetime] = None) -> Optional[dict]:
    """Turn one raw event into a canonical event dict, or return None if it
    fails the age filter (or is missing required fields).
    """
    name = _clean_text(raw.get("name") or "")
    start = raw.get("start")
    url = (raw.get("url") or "").strip()
    source = (raw.get("source") or "unknown").strip()

    if not name or start is None:
        return None
    if not isinstance(start, datetime):
        return None

    description = _clean_text(raw.get("description") or "")
    venue = _clean_text(raw.get("venue") or "")

    if not content_passes(
        name,
        description,
        venue,
        require_kid_signal=bool(raw.get("_require_kid_signal")),
    ):
        return None

    # Geographic guard: some feeds (Smithsonian via Trumba, notably) publish
    # affiliate events across the country. Reject those when the source is
    # marked require_dmv_location.
    if raw.get("_require_dmv_location") and looks_out_of_dmv(venue):
        return None

    passes, reason = age_passes(raw.get("age"))
    if not passes:
        return None

    end = raw.get("end") if isinstance(raw.get("end"), datetime) else None

    # If the source gave us a venue string but no venue_key, try to infer one
    # from the venue text — MCPL library branches, for instance, arrive with
    # "Rockville Memorial Library" and we know that maps to mcpl-rockville.
    venue_key = raw.get("venue_key") or distance.infer_venue_key(venue)

    band = distance.band_for(
        lat=raw.get("lat"),
        lng=raw.get("lng"),
        venue_key=venue_key,
    )

    cost_type = raw.get("cost_type") or "free"
    cost_label = raw.get("cost_label") or ("Free" if cost_type == "free" else "Paid")

    place = raw.get("place") or "indoor"

    now = now or datetime.now(timezone.utc)

    local_start = _to_local(start)
    local_end = _to_local(end)

    return {
        "id": _stable_id(source, name, start),
        "date": local_start.strftime("%Y-%m-%d"),
        "time": local_start.strftime("%H:%M"),
        "end": local_end.strftime("%H:%M") if local_end else None,
        "name": name,
        "venue": venue,
        "distance_mi_range": band or "unknown",
        "cost_type": cost_type,
        "cost_label": cost_label,
        "place": place,
        "state": raw.get("_state"),  # for the DC-vs-not filter
        "age": _clean_text(raw.get("age") or "") or "unspecified",
        "age_match_reason": reason,
        "description": description,
        "url": url,
        "source": source,
        "added_at": _iso(now),
        "updated_at": _iso(now),
        "expires_at": _iso(raw.get("expires_at")) if raw.get("expires_at") else None,
    }
