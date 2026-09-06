"""Shared utilities for HTML scrapers.

Every scraper module exposes:
    ID: str                        # unique short slug
    NAME: str                      # human-readable
    URL: str                       # canonical events page URL

    def fetch() -> list[dict]:
        '''Return a list of raw event dicts (shape per normalize.to_canonical).'''
"""

from __future__ import annotations

import requests

USER_AGENT = "little-dmv-bot/1.0 (+https://github.com/opoo-em/little-dmv)"
TIMEOUT = 30


def get(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text
