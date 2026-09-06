"""Age filter behavior — locks the rule from docs/decisions.md.

The rule: include events whose age range overlaps ~1-3yr. Exclude hard-only-babies
and hard-only-older (K+, elementary). Permissive on unrecognized strings.
"""

from __future__ import annotations

import pytest

from scripts.filter import age_passes


PASSING_CASES = [
    ("0-3 yrs", "range-0-3yr"),
    ("0-5 yrs", "range-0-5yr"),
    ("1-4 years", "range-1-4yr"),
    ("2-5", "range-2-5yr"),
    ("ages 1 to 3", "range-1-3yr"),
    ("All ages", "all-ages"),
    ("Family friendly", "all-ages"),
    ("everyone welcome", "all-ages"),
    ("Toddlers", "toddler"),
    ("preschool", "preschool"),
    ("preschooler", "preschool"),
    ("3+", "open-3+"),
    ("12 months", "months-12mo"),  # 12mo = 1yr, meets floor
    ("18 months and up", "months-18mo"),
    ("", "unspecified"),
    (None, "unspecified"),
    ("weird registration required", "unrecognized"),
]


FAILING_CASES = [
    ("5+ years", "too-old-5+"),
    ("Kindergarten and up", "kindergarten-or-older"),
    ("Grades 1-5", "kindergarten-or-older"),
    ("school age", "kindergarten-or-older"),
    ("elementary students", "kindergarten-or-older"),
    ("4 months only", "babies-only-4mo"),
    ("Infants only", "babies-only"),
    ("newborns", "babies-only"),
    ("ages 6-10", "too-old-6+"),
    ("ages 8-12", "too-old-8+"),
]


@pytest.mark.parametrize("raw,expected_reason", PASSING_CASES)
def test_passing(raw, expected_reason):
    passes, reason = age_passes(raw)
    assert passes, f"expected pass for {raw!r}, got fail ({reason})"
    assert reason == expected_reason, f"reason mismatch for {raw!r}: {reason} != {expected_reason}"


@pytest.mark.parametrize("raw,expected_reason", FAILING_CASES)
def test_failing(raw, expected_reason):
    passes, reason = age_passes(raw)
    assert not passes, f"expected fail for {raw!r}, got pass ({reason})"
    assert reason == expected_reason, f"reason mismatch for {raw!r}: {reason} != {expected_reason}"
