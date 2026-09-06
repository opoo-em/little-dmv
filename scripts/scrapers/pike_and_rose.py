"""Pike & Rose (North Bethesda) events scraper.

Mixed-use development with an active kid-events calendar — weekend farmers
market, seasonal kids' programming, holiday events. Federal Realty tenant, and
their sites usually publish Schema.org JSON-LD.
"""

from __future__ import annotations

from . import base, jsonld

ID = "pike-and-rose"
NAME = "Pike & Rose"
URL = "https://www.pikeandrose.com/events"


def fetch() -> list[dict]:
    html = base.get(URL)
    events = jsonld.extract_events(html)
    for e in events:
        e.setdefault("venue", "Pike & Rose")
        e["venue_key"] = "pike-and-rose"
        e.setdefault("place", "outdoor")
        e["source"] = ID
    return events
