"""Bethesda Row events scraper.

Retail plaza with seasonal family events (Winter Wonderland, Small Business
Saturday, Cherry Blossom weekend). Squarespace / Elementor stack — JSON-LD
tends to be present on individual event pages but the aggregate calendar page
may not carry all entries. Refine per-site if JSON-LD returns light.
"""

from __future__ import annotations

from . import base, jsonld

ID = "bethesda-row"
NAME = "Bethesda Row"
URL = "https://bethesdarow.com/events/"


def fetch() -> list[dict]:
    html = base.get(URL)
    events = jsonld.extract_events(html)
    for e in events:
        e.setdefault("venue", "Bethesda Row")
        e["venue_key"] = "bethesda-row"
        e.setdefault("place", "outdoor")
        e["source"] = ID
    return events
