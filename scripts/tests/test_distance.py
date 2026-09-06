"""Distance banding — locks the 5-band mapping from docs/decisions.md."""

from __future__ import annotations

import os
from unittest import mock

import pytest

from scripts.distance import band_for, to_band


@pytest.mark.parametrize(
    "miles,band",
    [
        (0.0, "0-5"),
        (4.9, "0-5"),
        (5.0, "0-5"),
        (5.1, "6-10"),
        (10.0, "6-10"),
        (10.5, "11-15"),
        (15.0, "11-15"),
        (16.0, "16-20"),
        (20.0, "16-20"),
        (20.1, "20+"),
        (100.0, "20+"),
    ],
)
def test_to_band_boundaries(miles, band):
    assert to_band(miles) == band


def test_band_for_returns_none_without_home_coords():
    with mock.patch.dict(os.environ, {}, clear=True):
        assert band_for(lat=39.0, lng=-77.1) is None


def test_band_for_with_venue_key():
    # Rockville-ish home; Rockville library should be 0-5.
    with mock.patch.dict(os.environ, {"HOME_LAT": "39.085", "HOME_LNG": "-77.153"}):
        assert band_for(venue_key="mcpl-rockville") == "0-5"


def test_band_for_missing_venue_key():
    with mock.patch.dict(os.environ, {"HOME_LAT": "39.085", "HOME_LNG": "-77.153"}):
        assert band_for(venue_key="not-a-real-venue") is None


def test_band_for_explicit_coords_wins_over_venue_key():
    # Explicit coords for a spot 25mi away override the venue-key lookup.
    with mock.patch.dict(os.environ, {"HOME_LAT": "39.085", "HOME_LNG": "-77.153"}):
        assert band_for(lat=39.5, lng=-76.7, venue_key="mcpl-rockville") == "20+"
