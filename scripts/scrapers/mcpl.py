"""MCPL (Montgomery County Public Library) events scraper — fallback.

MCPL runs their calendar on Springshare LibCal. The preferred path is to add
the LibCal iCal URL to sources.yaml (see docs/sources.md → Investigation
notes → MCPL). This scraper is the fallback if iCal isn't available or hasn't
been verified yet.

LibCal event listing pages typically emit Schema.org Event JSON-LD for SEO,
so the shared extractor usually works. If the site changes, patch here.

Volume note: MCPL is the highest-volume source for Little DMV. Storytimes
alone run daily across ~20 branches. Dedupe against iCal (source='mcpl')
so we don't double-render.
"""

from __future__ import annotations

from . import base, jsonld

ID = "mcpl"
NAME = "MCPL"
# Landing page for the kids' calendar — LibCal typically at mcpl.libcal.com.
# If the URL below returns nothing, try the county library site's calendar
# page instead and update this constant.
URL = "https://mcpl.libcal.com/calendar/kids"


def fetch() -> list[dict]:
    html = base.get(URL)
    events = jsonld.extract_events(html)
    for e in events:
        # Venue string from JSON-LD names the branch; keep it.
        e.setdefault("place", "indoor")
        e.setdefault("cost_type", "free")
        e.setdefault("cost_label", "Free")
        e["source"] = ID
    return events
