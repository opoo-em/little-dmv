"""JSON-LD Schema.org Event extractor.

Most modern venue sites embed Schema.org Event objects in <script type="application/ld+json">.
When present, this is the most reliable extraction path. Each concrete scraper
should try this first and fall back to per-site parsing only if it comes back empty.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Iterable

from bs4 import BeautifulSoup
from dateutil import parser as date_parser


def extract_events(html: str) -> list[dict]:
    """Return a list of raw event dicts pulled from JSON-LD blobs in the page."""
    soup = BeautifulSoup(html, "html.parser")
    out: list[dict] = []
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for node in _walk(data):
            if _is_event(node):
                event = _to_raw(node)
                if event:
                    out.append(event)
    return out


def _walk(node) -> Iterable[dict]:
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)


def _is_event(node: dict) -> bool:
    t = node.get("@type")
    if isinstance(t, list):
        return any("Event" in str(x) for x in t)
    return t is not None and "Event" in str(t)


def _to_raw(node: dict) -> dict | None:
    name = (node.get("name") or "").strip()
    start_raw = node.get("startDate")
    if not name or not start_raw:
        return None
    try:
        start = date_parser.isoparse(start_raw)
    except (ValueError, TypeError):
        try:
            start = date_parser.parse(start_raw)
        except (ValueError, TypeError):
            return None

    end = None
    end_raw = node.get("endDate")
    if end_raw:
        try:
            end = date_parser.parse(end_raw)
        except (ValueError, TypeError):
            end = None

    loc = node.get("location") or {}
    if isinstance(loc, list):
        loc = loc[0] if loc else {}
    venue = ""
    if isinstance(loc, dict):
        venue = (loc.get("name") or "").strip()

    offers = node.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    cost_type = "free"
    cost_label = "Free"
    if isinstance(offers, dict):
        price = offers.get("price")
        if price and str(price) not in ("0", "0.0", "0.00", ""):
            cost_type = "paid"
            currency = offers.get("priceCurrency", "USD")
            cost_label = f"${price} {currency}" if currency != "USD" else f"${price}"

    url = (node.get("url") or "").strip()

    return {
        "name": name,
        "start": start,
        "end": end,
        "venue": venue,
        "description": (node.get("description") or "").strip(),
        "url": url,
        "cost_type": cost_type,
        "cost_label": cost_label,
        "age": _extract_audience(node),
    }


def _extract_audience(node: dict) -> str:
    aud = node.get("audience") or {}
    if isinstance(aud, list):
        aud = aud[0] if aud else {}
    if isinstance(aud, dict):
        parts = []
        for key in ("audienceType", "name", "suggestedMinAge", "suggestedMaxAge"):
            v = aud.get(key)
            if v:
                parts.append(f"{key}:{v}")
        if parts:
            return " ".join(parts)
    return ""
