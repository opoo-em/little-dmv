"""Normalization — locks the raw → canonical schema conversion."""

from __future__ import annotations

from datetime import datetime, timezone

from scripts.normalize import to_canonical


def _now():
    return datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def test_basic_canonical():
    raw = {
        "name": "Baby Storytime",
        # 14:30 UTC = 10:30 AM Eastern (DST). Display is always local.
        "start": datetime(2026, 9, 13, 14, 30, tzinfo=timezone.utc),
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


def test_html_entities_and_tags_stripped_from_description():
    raw = {
        "name": "Baby Storytime",
        "start": datetime(2026, 9, 13, 10, 30, tzinfo=timezone.utc),
        "url": "https://example.com",
        "source": "mcpl",
        "description": "&lt;p&gt;Come join us &amp; sing along [&hellip;]&lt;/p&gt;\\n",
    }
    e = to_canonical(raw, now=_now())
    assert e is not None
    assert "<" not in e["description"]
    assert "&lt;" not in e["description"]
    assert "&amp;" not in e["description"]
    assert "&hellip;" not in e["description"]
    assert "\\n" not in e["description"]
    assert "Come join us & sing along" in e["description"]


def test_html_entities_in_name_decoded():
    raw = {
        "name": "Victorian Lyric Opera Company Presents &#8220;Haddon Hall&#8221;",
        "start": datetime(2026, 9, 13, 20, 0, tzinfo=timezone.utc),
        "url": "https://example.com",
        "source": "test",
    }
    e = to_canonical(raw, now=_now())
    # This one is filtered out for "opera company", so it's None. Verify the
    # cleanup path separately by using a benign title.
    raw["name"] = "Family Fun &amp; Games"
    e = to_canonical(raw, now=_now())
    assert e is not None
    assert e["name"] == "Family Fun & Games"


def test_content_filter_rejects_adult_event():
    raw = {
        "name": "Planning Commission Meeting",
        "start": datetime(2026, 9, 13, 19, 0, tzinfo=timezone.utc),
        "url": "https://example.com",
        "source": "rockville-city",
    }
    assert to_canonical(raw, now=_now()) is None


def test_require_kid_signal_rejects_generic_event():
    raw = {
        "name": "Community Fun Day",
        "start": datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc),
        "url": "https://example.com",
        "source": "rockville-city",
        "description": "Come enjoy the afternoon.",
        "_require_kid_signal": True,
    }
    assert to_canonical(raw, now=_now()) is None


def test_require_kid_signal_keeps_toddler_program():
    raw = {
        "name": "Little Sprouts",
        "start": datetime(2026, 9, 13, 10, 0, tzinfo=timezone.utc),
        "url": "https://example.com",
        "source": "rockville-city",
        "description": "Toddler nature program for our youngest naturalists.",
        "_require_kid_signal": True,
    }
    assert to_canonical(raw, now=_now()) is not None


def test_utc_time_converted_to_eastern():
    # 22:30 UTC on 2026-09-13 = 6:30 PM EDT (pajama storytime slot).
    raw = {
        "name": "Pajama Storytime",
        "start": datetime(2026, 9, 13, 22, 30, tzinfo=timezone.utc),
        "url": "https://example.com",
        "source": "mcpl",
    }
    e = to_canonical(raw, now=_now())
    assert e["time"] == "18:30"


def test_dmv_filter_rejects_new_hampshire():
    raw = {
        "name": "Duck Race",
        "start": datetime(2026, 9, 12, 14, 0, tzinfo=timezone.utc),
        "url": "https://example.com",
        "source": "smithsonian",
        "venue": "Auburn Village Auburn, New Hampshire",
        "_require_dmv_location": True,
    }
    assert to_canonical(raw, now=_now()) is None


def test_dmv_filter_keeps_dmv_venue():
    raw = {
        "name": "Spark!Lab",
        "start": datetime(2026, 9, 12, 14, 0, tzinfo=timezone.utc),
        "url": "https://example.com",
        "source": "smithsonian",
        "venue": "American History Museum",
        "_require_dmv_location": True,
    }
    assert to_canonical(raw, now=_now()) is not None


def test_smithsonian_associates_rejected_everywhere():
    raw = {
        "name": "The Fight for Nazi-Looted Art",
        "start": datetime(2026, 9, 12, 22, 30, tzinfo=timezone.utc),
        "url": "https://smithsonianassociates.org/x",
        "source": "smithsonian",
        "venue": "smithsonianassociates.org",
    }
    assert to_canonical(raw, now=_now()) is None


def test_state_stamped_on_event():
    raw = {
        "name": "Storytime",
        "start": datetime(2026, 9, 13, 14, 30, tzinfo=timezone.utc),
        "url": "https://example.com",
        "source": "mcpl",
        "_state": "MD",
    }
    e = to_canonical(raw, now=_now())
    assert e["state"] == "MD"


def test_venue_inference_gives_distance_band():
    # When the source doesn't set venue_key but the venue string matches a
    # known MCPL branch, distance banding should still work.
    import os
    os.environ["HOME_LAT"] = "39.0845"
    os.environ["HOME_LNG"] = "-77.1528"
    try:
        raw = {
            "name": "Baby Storytime",
            "start": datetime(2026, 9, 13, 14, 30, tzinfo=timezone.utc),
            "url": "https://example.com",
            "source": "mcpl",
            "venue": "Twinbrook Library",
        }
        e = to_canonical(raw, now=_now())
        # Twinbrook is a few miles from Rockville home.
        assert e["distance_mi_range"] in ("0-5", "6-10")
    finally:
        del os.environ["HOME_LAT"]
        del os.environ["HOME_LNG"]


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
