"""Smithsonian National Zoo scraper.

The Zoo has its own event program separate from Smithsonian.si.edu — animal
meet-and-greets, ZooLights, Boo at the Zoo, keeper talks. Their events page
usually embeds Schema.org JSON-LD.
"""

from __future__ import annotations

from . import base, jsonld

ID = "national-zoo"
NAME = "Smithsonian National Zoo"
URL = "https://nationalzoo.si.edu/events"


def fetch() -> list[dict]:
    html = base.get(URL)
    events = jsonld.extract_events(html)
    for e in events:
        e.setdefault("venue", "Smithsonian National Zoo")
        e["venue_key"] = "national-zoo"
        e.setdefault("place", "outdoor")
        e["source"] = ID
    return events
