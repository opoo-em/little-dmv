"""Load seasonal / annual events from data/seasonal.json into the pipeline.

Two shapes supported per entry:
    - date: "YYYY-MM-DD"                         (one specific date)
    - window: {"start": "YYYY-MM-DD",
               "end":   "YYYY-MM-DD"}            (recurring daily within the range)

For a window, one canonical event is emitted per day within the LOOKAHEAD_DAYS
horizon — so a 6-week pumpkin patch shows up every day it's actually open, but
only for the current 3-week planning window. Past-window entries are silently
skipped (annuals get bumped by hand each year).
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

SEASONAL_FILE = Path(__file__).resolve().parent.parent / "data" / "seasonal.json"
LOOKAHEAD_DAYS = 21


def _iter_dates(start: date, end: date) -> Iterable[date]:
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def load(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    horizon = (now + timedelta(days=LOOKAHEAD_DAYS)).date()
    today = now.date()

    if not SEASONAL_FILE.exists():
        return []

    with SEASONAL_FILE.open() as f:
        data = json.load(f)

    out: list[dict] = []
    for entry in data.get("events", []):
        time = entry.get("time", "10:00")
        end_time = entry.get("end")

        if "date" in entry:
            d = date.fromisoformat(entry["date"])
            if d < today or d > horizon:
                continue
            out.append(_expand_one(entry, d, time, end_time))
            continue

        if "window" in entry:
            w = entry["window"]
            w_start = date.fromisoformat(w["start"])
            w_end = date.fromisoformat(w["end"])
            eff_start = max(w_start, today)
            eff_end = min(w_end, horizon)
            for d in _iter_dates(eff_start, eff_end):
                out.append(_expand_one(entry, d, time, end_time))

    return out


def _expand_one(entry: dict, on: date, time: str, end_time: str | None) -> dict:
    start = datetime.fromisoformat(f"{on.isoformat()}T{time}").replace(tzinfo=timezone.utc)
    end = None
    if end_time:
        end = datetime.fromisoformat(f"{on.isoformat()}T{end_time}").replace(tzinfo=timezone.utc)
    return {
        "name": entry["name"],
        "start": start,
        "end": end,
        "venue": entry.get("venue", ""),
        "venue_key": entry.get("venue_key"),
        "place": entry.get("place", "outdoor"),
        "cost_type": entry.get("cost_type", "free"),
        "cost_label": entry.get("cost_label", "Free"),
        "age": entry.get("age", "All ages"),
        "url": entry.get("url", ""),
        "description": entry.get("description", ""),
        "source": entry.get("source", "seasonal"),
    }
