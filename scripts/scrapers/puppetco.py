"""The Puppet Co — Tiny Tots track scraper.

The Puppet Co is on the grounds of Glen Echo Park. Their Tiny Tots track is
explicitly designed for 18mo-4yr — 30 min runtime, no dark room, no surprising
loud noises, open theatre doors. Age-perfect for Felix.

Chosen over a general Glen Echo scraper because Glen Echo's own calendar is
mostly adult programming and the youngest kid events on GE's site are 4+.

Strategy: try JSON-LD first (most theatre sites embed Schema.org Event nodes
on show pages); patch with per-site HTML parsing here if empty.
"""

from __future__ import annotations

from . import base, jsonld

ID = "puppetco-tinytots"
NAME = "The Puppet Co — Tiny Tots"
URL = "https://thepuppetco.org/tiny-tots"


def fetch() -> list[dict]:
    html = base.get(URL)
    events = jsonld.extract_events(html)
    for e in events:
        e.setdefault("venue", "The Puppet Co at Glen Echo Park")
        e["venue_key"] = "puppetco-tinytots"
        e["place"] = "indoor"
        e["source"] = ID
        # Tiny Tots is explicitly designed for 18mo-4yr. Every event on this
        # page is age-appropriate by construction; the filter will still QA
        # via age_match_reason but shouldn't reject any of these.
        if not e.get("age"):
            e["age"] = "18 months - 4 years"
    return events
