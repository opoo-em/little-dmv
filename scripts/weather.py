"""National Weather Service forecast — stamped onto outdoor events.

Em asked for this in decisions.md as an example partnership contribution.
Implementation: hit NWS forecast API once per pipeline run for HOME_LAT/LNG,
build a {date: forecast} map for the next 7 days, stamp matching outdoor
events with a `weather` field.

NWS API is free, government, requires no API key, and has excellent DMV
coverage. Rate limits are generous but we still cache once per run.

Skips silently if HOME_LAT/HOME_LNG aren't set — outdoor events just won't
carry weather info. Same failure mode as distance banding.

Weather is intentionally per-DAY, not per-hour. A toddler mom scanning a
Saturday makes a go/no-go call on the day, not the 2-4pm window. Adding
hourly matching per event start time would be more precise but more
brittle for less lift.
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import requests

USER_AGENT = "little-dmv-bot/1.0 (github.com/opoo-em/little-dmv)"


def _home() -> Optional[tuple[float, float]]:
    lat, lng = os.environ.get("HOME_LAT"), os.environ.get("HOME_LNG")
    if not lat or not lng:
        return None
    try:
        return float(lat), float(lng)
    except ValueError:
        return None


def build_forecast_map() -> dict[str, dict]:
    """Return {"YYYY-MM-DD": {"summary": "Sunny", "high_f": 82, "low_f": 65,
                              "precip_pct": 10}} for the next ~7 days.

    Empty dict on any failure — pipeline continues without weather.
    """
    home = _home()
    if home is None:
        print("  weather: HOME_LAT/HOME_LNG not set, skipping", file=sys.stderr)
        return {}

    try:
        points_url = f"https://api.weather.gov/points/{home[0]:.4f},{home[1]:.4f}"
        resp = requests.get(points_url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
        forecast_url = resp.json()["properties"]["forecast"]

        resp = requests.get(forecast_url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
        periods = resp.json()["properties"]["periods"]
    except Exception as exc:
        print(f"  weather: FAILED — {exc}", file=sys.stderr)
        return {}

    # NWS gives 12h periods (daytime + overnight). Reduce to per-day:
    #   - summary + precip_pct from the DAYTIME period (isDaytime == true)
    #   - high_f from daytime period.temperature (F)
    #   - low_f from following overnight period
    per_day: dict[str, dict] = {}
    for p in periods:
        start = datetime.fromisoformat(p["startTime"])
        d = start.date().isoformat()
        entry = per_day.setdefault(d, {})
        if p.get("isDaytime"):
            entry["summary"] = p.get("shortForecast", "")
            entry["high_f"] = p.get("temperature")
            pp = p.get("probabilityOfPrecipitation") or {}
            entry["precip_pct"] = pp.get("value") if isinstance(pp, dict) else pp
        else:
            entry.setdefault("low_f", p.get("temperature"))

    print(f"  weather: {len(per_day)} days of NWS forecast", file=sys.stderr)
    return per_day


def stamp(events: list[dict], forecast: dict[str, dict]) -> None:
    """Mutate the events list in place: add `weather` to each outdoor event
    whose date is in the forecast window.
    """
    if not forecast:
        return
    for e in events:
        if e.get("place") != "outdoor":
            continue
        wx = forecast.get(e["date"])
        if wx and wx.get("summary"):
            e["weather"] = wx
