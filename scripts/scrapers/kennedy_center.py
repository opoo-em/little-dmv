"""Kennedy Center Millennium Stage scraper.

Kennedy Center's site is React-heavy — many events load via client-side JS
and won't show up in a static HTML fetch. That said, the site does emit
Schema.org Event JSON-LD in server-rendered markup for SEO. Try that first.

If this scraper comes back empty on the first Actions run, the fallback is
to hit the JSON API directly. Their API pattern (historically) is:
    https://www.kennedy-center.org/api/events?...
The exact params drift over time — pull DevTools → Network on the calendar
page to snapshot the current call.

Millennium Stage is the free daily performance program — most events are free
and family-friendly-adjacent (some are — not all). Age filtering downstream
will drop the not-a-fit ones.
"""

from __future__ import annotations

from . import base, jsonld

ID = "kennedy-center-millennium"
NAME = "Kennedy Center Millennium Stage"
URL = "https://www.kennedy-center.org/whats-on/millennium-stage/"


def fetch() -> list[dict]:
    html = base.get(URL)
    events = jsonld.extract_events(html)
    for e in events:
        e.setdefault("venue", "Kennedy Center Millennium Stage")
        e["venue_key"] = "kennedy-center"
        e["place"] = "indoor"
        # Millennium Stage is free by design — override any missing cost data.
        e.setdefault("cost_type", "free")
        e.setdefault("cost_label", "Free")
        e["source"] = ID
    return events
