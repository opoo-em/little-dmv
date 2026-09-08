"""Distance calculation and banding.

Reads reference home coordinates from environment variables HOME_LAT and
HOME_LNG (set as GitHub Secrets in production). Never writes raw distances or
coordinates to the output — only the band, per docs/decisions.md.
"""

from __future__ import annotations

import math
import os
from typing import Optional

BANDS = ["0-5", "6-10", "11-15", "16-20", "20+"]


def _home() -> Optional[tuple[float, float]]:
    lat = os.environ.get("HOME_LAT")
    lng = os.environ.get("HOME_LNG")
    if lat is None or lng is None:
        return None
    try:
        return float(lat), float(lng)
    except ValueError:
        return None


def haversine_mi(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R_MI = 3958.7613
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * R_MI * math.asin(math.sqrt(a))


def to_band(miles: float) -> str:
    if miles <= 5:
        return "0-5"
    if miles <= 10:
        return "6-10"
    if miles <= 15:
        return "11-15"
    if miles <= 20:
        return "16-20"
    return "20+"


# Fallback venue coordinates for sources that give us a venue name but no
# lat/lng. Keep this table modest — add rows only for high-volume repeat
# venues. Coordinates are public info (published street addresses geocoded once).
VENUE_COORDS: dict[str, tuple[float, float]] = {
    # Montgomery County libraries (MCPL branches most relevant to a Rockville-ish home)
    "mcpl-rockville": (39.0850, -77.1528),
    "mcpl-twinbrook": (39.0724, -77.1216),
    "mcpl-aspenhill": (39.0687, -77.0730),
    "mcpl-bethesda": (38.9847, -77.0947),
    "mcpl-davis": (39.0348, -77.0693),
    "mcpl-gaithersburg": (39.1439, -77.2013),
    "mcpl-germantown": (39.1750, -77.2717),
    "mcpl-kensington-park": (39.0334, -77.0757),
    "mcpl-olney": (39.1533, -77.0645),
    "mcpl-potomac": (39.0187, -77.2085),
    "mcpl-quince-orchard": (39.1394, -77.1878),
    "mcpl-white-oak": (39.0400, -76.9877),
    "mcpl-wheaton": (39.0389, -77.0553),
    # More MCPL branches — public addresses, approximate but within a
    # few hundred meters (haversine bands are 5-mile bins so this is fine).
    "mcpl-mcgee": (38.9954, -77.0288),           # Brigadier Gen. C.E. McGee Library (Silver Spring)
    "mcpl-chevy-chase": (38.9822, -77.0805),
    "mcpl-connie-morella": (38.9836, -77.0951),  # formerly Bethesda Regional
    "mcpl-little-falls": (38.9670, -77.1155),
    "mcpl-long-branch": (38.9942, -77.0210),
    "mcpl-maggie-nightingale": (39.1502, -77.4108),  # Poolesville
    "mcpl-marilyn-praisner": (39.1023, -76.9410),    # Burtonsville
    # Rockville-city venues that aren't the town square
    "croydon-creek-nature-center": (39.0937, -77.1425),
    "rockville-police-station": (39.0843, -77.1554),
    # Montgomery Parks kid-heavy venues
    "cabin-john-regional-park": (39.0289, -77.1720),
    "wheaton-regional-park": (39.0451, -77.0355),
    "brookside-gardens": (39.0692, -77.0378),
    "meadowside-nature-center": (39.1275, -77.1120),
    "locust-grove-nature-center": (39.0107, -77.1728),
    "black-hill-regional-park": (39.2115, -77.2854),
    "glen-echo-park": (38.9689, -77.1428),
    # Kid-specific / commercial
    "butlers-orchard": (39.2199, -77.2481),
    # DC institutions
    "kennedy-center": (38.8955, -77.0555),
    "national-building-museum": (38.8975, -77.0175),
    "national-childrens-museum": (38.8940, -77.0281),
    "smithsonian-national-mall": (38.8888, -77.0230),  # centroid of the mall museums
    "national-gallery-of-art": (38.8913, -77.0199),
    "national-zoo": (38.9296, -77.0498),
    # Farmers markets / mixed-use
    "rockville-town-square": (39.0839, -77.1519),
    "pike-and-rose": (39.0510, -77.1174),
    "bethesda-central-farm-market": (38.9807, -77.0930),
    "downtown-silver-spring": (38.9944, -77.0261),
    "bethesda-row": (38.9807, -77.0951),
    "congressional-plaza": (39.0578, -77.1211),
}


# Substrings we can use to infer a venue_key from a raw venue name string
# when the source (an iCal feed, usually) doesn't set one explicitly. The
# match is a substring test on lowercased venue text; more specific keys
# should come first so "Wheaton Library" matches mcpl-* before falling
# through to the park.
_VENUE_INFERENCE: list[tuple[str, str]] = [
    ("rockville memorial library", "mcpl-rockville"),
    ("twinbrook library", "mcpl-twinbrook"),
    ("aspen hill library", "mcpl-aspenhill"),
    ("bethesda library", "mcpl-bethesda"),
    ("davis library", "mcpl-davis"),
    ("gaithersburg library", "mcpl-gaithersburg"),
    ("germantown library", "mcpl-germantown"),
    ("kensington park library", "mcpl-kensington-park"),
    ("olney library", "mcpl-olney"),
    ("potomac library", "mcpl-potomac"),
    ("quince orchard library", "mcpl-quince-orchard"),
    ("white oak library", "mcpl-white-oak"),
    ("wheaton library", "mcpl-wheaton"),
    ("brigadier general charles e", "mcpl-mcgee"),
    ("mcgee library", "mcpl-mcgee"),
    ("chevy chase library", "mcpl-chevy-chase"),
    ("connie morella library", "mcpl-connie-morella"),
    ("little falls library", "mcpl-little-falls"),
    ("long branch library", "mcpl-long-branch"),
    ("maggie nightingale library", "mcpl-maggie-nightingale"),
    ("marilyn j. praisner library", "mcpl-marilyn-praisner"),
    ("marilyn j praisner library", "mcpl-marilyn-praisner"),
    ("praisner library", "mcpl-marilyn-praisner"),
    ("croydon creek nature center", "croydon-creek-nature-center"),
    ("square in rockville town center", "rockville-town-square"),
    ("rockville town square", "rockville-town-square"),
    ("rockville town center", "rockville-town-square"),
    ("rockville city police station", "rockville-police-station"),
    ("wheaton regional park", "wheaton-regional-park"),
    ("cabin john regional park", "cabin-john-regional-park"),
    ("brookside gardens", "brookside-gardens"),
    ("meadowside nature center", "meadowside-nature-center"),
    ("locust grove nature center", "locust-grove-nature-center"),
    ("black hill regional park", "black-hill-regional-park"),
    ("glen echo park", "glen-echo-park"),
    ("butler's orchard", "butlers-orchard"),
    ("butlers orchard", "butlers-orchard"),
    ("national zoo", "national-zoo"),
    ("kennedy center", "kennedy-center"),
    ("air and space museum", "smithsonian-national-mall"),
    ("american history museum", "smithsonian-national-mall"),
    ("american indian museum", "smithsonian-national-mall"),
    ("african american history and culture", "smithsonian-national-mall"),
    ("natural history museum", "smithsonian-national-mall"),
    ("portrait gallery", "smithsonian-national-mall"),
    ("smithsonian gardens", "smithsonian-national-mall"),
    ("postal museum", "smithsonian-national-mall"),
    ("anacostia community museum", "smithsonian-national-mall"),
    ("african art museum", "smithsonian-national-mall"),
    ("asian art museum", "smithsonian-national-mall"),
    ("american art museum", "smithsonian-national-mall"),
    # Catch-all for events whose venue is just "Smithsonian" without a
    # specific museum — put LAST so specific museum matches win.
    ("smithsonian", "smithsonian-national-mall"),
]


def infer_venue_key(venue: str) -> Optional[str]:
    """Best-effort mapping from a venue name string to a VENUE_COORDS key.

    Returns None when no known substring matches — the caller then treats
    the event as unknown-distance. Case-insensitive substring test.
    """
    if not venue:
        return None
    v = venue.lower()
    for needle, key in _VENUE_INFERENCE:
        if needle in v:
            return key
    return None


def band_for(
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    venue_key: Optional[str] = None,
) -> Optional[str]:
    """Return the distance band string, or None if we can't calculate.

    Prefers explicit lat/lng if given; falls back to VENUE_COORDS lookup.
    Returns None when HOME_LAT/HOME_LNG is not set (safe for local dev without
    the secret — a null band means the UI still shows the event, just without
    distance info).
    """
    home = _home()
    if home is None:
        return None

    if lat is None or lng is None:
        if venue_key and venue_key in VENUE_COORDS:
            lat, lng = VENUE_COORDS[venue_key]
        else:
            return None

    miles = haversine_mi(home[0], home[1], lat, lng)
    return to_band(miles)
