"""National Building Museum scraper.

NBM has a strong family programming lineup (Building Zone, Discovery Cart,
storytimes, hard-hat tours). The events index is at /programs-events/ with each
event on its own detail page. Modern NBM stack emits Schema.org Event JSON-LD.
"""

from __future__ import annotations

from . import base, jsonld

ID = "national-building-museum"
NAME = "National Building Museum"
URL = "https://www.nbm.org/programs-events/"


def fetch() -> list[dict]:
    html = base.get(URL)
    events = jsonld.extract_events(html)
    for e in events:
        e.setdefault("venue", "National Building Museum")
        e["venue_key"] = "national-building-museum"
        e["place"] = "indoor"
        e["source"] = ID
    return events
