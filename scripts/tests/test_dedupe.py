"""Dedupe — locks the (date, name, venue) key and first-wins ordering rule."""

from __future__ import annotations

from scripts.main import dedupe


def _event(date, name, venue, source="a"):
    return {
        "date": date,
        "name": name,
        "venue": venue,
        "source": source,
        "time": "10:00",
    }


def test_dedupe_removes_exact_repeats():
    events = [
        _event("2026-09-13", "Storytime", "Rockville Library"),
        _event("2026-09-13", "Storytime", "Rockville Library"),
    ]
    assert len(dedupe(events)) == 1


def test_dedupe_first_wins_source_order():
    events = [
        _event("2026-09-13", "Storytime", "Rockville Library", source="mcpl"),
        _event("2026-09-13", "Storytime", "Rockville Library", source="kidfriendly-dc"),
    ]
    result = dedupe(events)
    assert len(result) == 1
    assert result[0]["source"] == "mcpl"


def test_dedupe_case_insensitive_and_whitespace_tolerant():
    events = [
        _event("2026-09-13", "Storytime", "Rockville Library"),
        _event("2026-09-13", "  storytime  ", "ROCKVILLE LIBRARY"),
    ]
    assert len(dedupe(events)) == 1


def test_dedupe_keeps_same_name_different_dates():
    events = [
        _event("2026-09-13", "Storytime", "Rockville Library"),
        _event("2026-09-20", "Storytime", "Rockville Library"),
    ]
    assert len(dedupe(events)) == 2


def test_dedupe_keeps_same_name_different_venues():
    events = [
        _event("2026-09-13", "Storytime", "Rockville Library"),
        _event("2026-09-13", "Storytime", "Bethesda Library"),
    ]
    assert len(dedupe(events)) == 2
