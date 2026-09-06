"""Montgomery Parks scraper — HTML fallback.

Montgomery Parks runs WordPress with The Events Calendar plugin, which usually
serves iCal at /events/feed/ical/. Preferred path is to add that URL to
`sources.yaml` iCal section once verified.

If the iCal endpoint turns out to require auth, redirects, or doesn't exist,
this scraper is the fallback — it pulls JSON-LD Event nodes from the public
events listing page.
"""

from __future__ import annotations

from . import base, jsonld

ID = "montgomery-parks"
NAME = "Montgomery Parks"
URL = "https://www.montgomeryparks.org/events/"


def fetch() -> list[dict]:
    html = base.get(URL)
    events = jsonld.extract_events(html)
    for e in events:
        # Venue name comes from JSON-LD per event; leave it. Almost all
        # Montgomery Parks events are outdoors.
        e.setdefault("place", "outdoor")
        e["source"] = ID
    return events
