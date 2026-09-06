"""Normalization — locks the raw → canonical schema conversion."""

from __future__ import annotations

from datetime import datetime, timezone

from scripts.normalize import to_canonical


def _now():
    return datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def test_basic_canonical():
    raw = {
        "name": "Baby Storytime",
        "start": datetime(2026, 9, 13, 10, 30, tzinfo=timezone.utc),
        "url": "https://example.com/e/1",
        "source": "mcpl",
    }
    e = to_canonical(raw, now=_now())
    assert e is not None
    assert e["date"] == "2026-09-13"
    assert e["time"] == "10:30"
    assert e["end"] is None
    assert e["source"] == "mcpl"
    assert e["cost_type"] == "free"
    assert e["cost_label"] == "Free"
    assert e["place"] == "indoor"
    assert e["age_match_reason"] == "unspecified"


def test_age_filter_rejects():
    raw = {
        "name": "Kindergarten Robotics",
        "start": datetime(2026, 9, 13, 10, 30, tzinfo=timezone.utc),
        "url": "https://example.com",
        "source": "test",
        "age": "Kindergarten+",
    }
    assert to_canonical(raw, now=_now()) is None


def test_paid_cost_carries_label():
    raw = {
        "name": "Farm Day",
        "start": datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
        "url": "https://example.com",
        "source": "butlers-orchard",
        "cost_type": "paid",
        "cost_label": "$18/person",
    }
    e = to_canonical(raw, now=_now())
    assert e is not None
    assert e["cost_type"] == "paid"
    assert e["cost_label"] == "$18/person"


def test_missing_name_returns_none():
    raw = {
        "name": "",
        "start": datetime(2026, 9, 13, 10, 0, tzinfo=timezone.utc),
        "url": "",
        "source": "x",
    }
    assert to_canonical(raw, now=_now()) is None


def test_missing_start_returns_none():
    raw = {"name": "Storytime", "url": "", "source": "x"}
    assert to_canonical(raw, now=_now()) is None


def test_id_is_stable_across_calls():
    raw = {
        "name": "Baby Storytime",
        "start": datetime(2026, 9, 13, 10, 30, tzinfo=timezone.utc),
        "url": "https://example.com/e/1",
        "source": "mcpl",
    }
    a = to_canonical(raw, now=_now())
    b = to_canonical(raw, now=_now())
    assert a["id"] == b["id"]
