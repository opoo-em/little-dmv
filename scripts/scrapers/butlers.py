"""Butler's Orchard scraper.

Butler's has a seasonal Family Fun Days schedule (spring strawberry picking,
summer u-pick, fall pumpkin patch / hayride / farm store events). The site is
Squarespace-shaped, which typically emits Schema.org Event JSON-LD on event
pages. Try JSON-LD first; if the page structure changes, patch here.

Notes
-----
- Butler's events run outdoors (place_default=outdoor) on a working farm.
  Overridden per-event if a specific listing marks otherwise.
- Ages usually family/all-ages; hard toddler exclusions are rare here.
- Distance key: butlers-orchard (see scripts/distance.py).
"""

from __future__ import annotations

from . import base, jsonld

ID = "butlers-orchard"
NAME = "Butler's Orchard"
URL = "https://butlersorchard.com/events/"


def fetch() -> list[dict]:
    html = base.get(URL)
    events = jsonld.extract_events(html)
    for e in events:
        e.setdefault("venue", "Butler's Orchard")
        e["venue_key"] = "butlers-orchard"
        e["place"] = "outdoor"
        e["source"] = ID
    return events
