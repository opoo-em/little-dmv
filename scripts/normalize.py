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
import re
from datetime import datetime, timezone
from typing import Any, Optional

from . import distance
from .filter import age_passes


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "event"


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
    name = (raw.get("name") or "").strip()
    start = raw.get("start")
    url = (raw.get("url") or "").strip()
    source = (raw.get("source") or "unknown").strip()

    if not name or start is None:
        return None
    if not isinstance(start, datetime):
        return None

    passes, reason = age_passes(raw.get("age"))
    if not passes:
        return None

    end = raw.get("end") if isinstance(raw.get("end"), datetime) else None

    band = distance.band_for(
        lat=raw.get("lat"),
        lng=raw.get("lng"),
        venue_key=raw.get("venue_key"),
    )

    cost_type = raw.get("cost_type") or "free"
    cost_label = raw.get("cost_label") or ("Free" if cost_type == "free" else "Paid")

    place = raw.get("place") or "indoor"

    now = now or datetime.now(timezone.utc)

    return {
        "id": _stable_id(source, name, start),
        "date": start.strftime("%Y-%m-%d"),
        "time": start.strftime("%H:%M"),
        "end": end.strftime("%H:%M") if end else None,
        "name": name,
        "venue": raw.get("venue") or "",
        "distance_mi_range": band or "unknown",
        "cost_type": cost_type,
        "cost_label": cost_label,
        "place": place,
        "age": raw.get("age") or "unspecified",
        "age_match_reason": reason,
        "description": (raw.get("description") or "").strip(),
        "url": url,
        "source": source,
        "added_at": _iso(now),
        "updated_at": _iso(now),
        "expires_at": _iso(raw.get("expires_at")) if raw.get("expires_at") else None,
    }
