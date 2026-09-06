"""National Children's Museum scraper.

NCM is on Squarespace-like tech and typically emits Schema.org Event JSON-LD
on its programs page. Straightforwardly kid-focused so nearly every event
passes the age filter.
"""

from __future__ import annotations

from . import base, jsonld

ID = "national-childrens-museum"
NAME = "National Children's Museum"
URL = "https://nationalchildrensmuseum.org/visit/events/"


def fetch() -> list[dict]:
    html = base.get(URL)
    events = jsonld.extract_events(html)
    for e in events:
        e.setdefault("venue", "National Children's Museum")
        e["venue_key"] = "national-childrens-museum"
        e["place"] = "indoor"
        e["source"] = ID
    return events
