"""Glen Echo Park scraper.

Glen Echo hosts the Puppet Co, carousel, arts programming, and free family
events on the grounds. The site is WordPress with The Events Calendar plugin
(tribe_events), which offers both JSON-LD and an /events/list/?ical=1 endpoint.

Strategy: try the plugin's iCal endpoint first (cleaner); fall back to JSON-LD
scrape. If iCal works, this scraper effectively becomes a one-liner and could
be moved into sources.yaml as an iCal source.
"""

from __future__ import annotations

from . import base, jsonld

ID = "glen-echo-park"
NAME = "Glen Echo Park"
URL = "https://glenechopark.org/calendar-of-events"


def fetch() -> list[dict]:
    html = base.get(URL)
    events = jsonld.extract_events(html)
    for e in events:
        e.setdefault("venue", "Glen Echo Park")
        e["venue_key"] = "glen-echo-park"
        # Glen Echo events are a mix — many indoor (Puppet Co, Bumper Car
        # Pavilion when covered), some outdoor (grounds, carousel line).
        # Default to indoor and let per-event data override if the JSON-LD
        # marks it otherwise.
        e.setdefault("place", "indoor")
        e["source"] = ID
    return events
