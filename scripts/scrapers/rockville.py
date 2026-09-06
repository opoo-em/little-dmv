"""City of Rockville events scraper.

Rockville runs a Drupal-based events calendar. Drupal Views sometimes emits
JSON-LD Event nodes; sometimes not. If JSON-LD comes back empty, this scraper
will need per-site parsing added.
"""

from __future__ import annotations

from . import base, jsonld

ID = "rockville-city"
NAME = "City of Rockville"
URL = "https://www.rockvillemd.gov/calendar.aspx"


def fetch() -> list[dict]:
    html = base.get(URL)
    events = jsonld.extract_events(html)
    for e in events:
        e.setdefault("venue", "Rockville")
        e.setdefault("place", "outdoor")
        e["source"] = ID
    return events
