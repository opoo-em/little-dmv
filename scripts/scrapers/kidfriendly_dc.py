"""KidFriendly DC aggregator scraper.

KidFriendly DC is a mom-run curation of the DMV kids' events. It's already an
aggregator, which means:
    (a) volume is high per fetch
    (b) items already pre-filtered for kid relevance
    (c) items include external URLs pointing at the original venue

Strategy: pull JSON-LD Event nodes; each event's `url` field points at the
original venue page. Because KFD is itself the source of the aggregation, the
`source` field is 'kidfriendly-dc' and `venue` is per-event from JSON-LD.

Dedupe: main.py de-duplicates against events from other sources by (name,
date, venue) — KFD often carries the same MCPL / Smithsonian event that
already came in via an iCal feed, and the iCal version wins.
"""

from __future__ import annotations

from . import base, jsonld

ID = "kidfriendly-dc"
NAME = "KidFriendly DC"
URL = "https://kidfriendlydc.com/events/"


def fetch() -> list[dict]:
    html = base.get(URL)
    events = jsonld.extract_events(html)
    for e in events:
        # Leave venue as-is from JSON-LD; KFD passes it through from source.
        e["source"] = ID
        # Place unknown at the aggregator level; leave to per-event JSON-LD.
        e.setdefault("place", "indoor")
    return events
