"""Age filter — the one non-user-facing filter, per docs/decisions.md.

Rule: keep events whose age range overlaps ~1-3 years (Felix's toddler range).
Exclude hard-only-babies (e.g. "hatchlings 4mo") and hard-only-older
(5+, kindergarten+, elementary).

Input is a raw age string (free-text from a source). Output is a tuple
(passes: bool, reason: str). The reason is written into event.age_match_reason
for QA per the schema.
"""

from __future__ import annotations

import re
from typing import Tuple

TARGET_MIN_YR = 1.0
TARGET_MAX_YR = 3.0

# Patterns are ordered — first match wins.
_ALL_AGES = re.compile(
    r"\b(all\s*ages|family(\s|-)*friendly|everyone|open\s+to\s+all)\b", re.I
)
_KINDER_PLUS = re.compile(r"\b(k(indergarten)?\s*[-+]?|k-\d|k\s*through)\b", re.I)
_ELEMENTARY = re.compile(r"\b(elementary|grades?\s*[1-9]|school[-\s]?age)\b", re.I)
_MONTHS_ONLY = re.compile(r"\b(\d+)\s*(mo|mos|months?)\b", re.I)
_YR_RANGE = re.compile(
    r"\b(\d+)\s*(?:-|to|–|—)\s*(\d+)\s*(yr|yrs|year|years)?\b", re.I
)
_YR_PLUS = re.compile(r"\b(\d+)\s*\+\s*(?:yr|yrs|year|years)?(?=\s|$|[^\w+])", re.I)
_AGES_N_TO_M = re.compile(r"\bages?\s*(\d+)\s*(?:-|to)\s*(\d+)\b", re.I)
_TODDLER = re.compile(r"\btoddler(s)?\b", re.I)
_BABY_INFANT = re.compile(r"\b(baby|babies|infant(s)?|newborn(s)?)\b", re.I)
_PRESCHOOL = re.compile(r"\b(pre[- ]?school|preschooler)\b", re.I)


def _overlap(lo: float, hi: float) -> bool:
    return not (hi < TARGET_MIN_YR or lo > TARGET_MAX_YR)


def age_passes(raw: str | None) -> Tuple[bool, str]:
    """Return (passes, reason)."""
    if not raw:
        # Unspecified age — permissive, per decisions.md.
        return True, "unspecified"

    s = raw.strip()

    if _ALL_AGES.search(s):
        return True, "all-ages"

    # Reject hard-only-older markers first — they'd otherwise get caught by
    # the year-range parser as e.g. "kindergarten" matching nothing.
    if _KINDER_PLUS.search(s) or _ELEMENTARY.search(s):
        return False, "kindergarten-or-older"

    m = _AGES_N_TO_M.search(s) or _YR_RANGE.search(s)
    if m:
        lo = float(m.group(1))
        hi = float(m.group(2))
        if _overlap(lo, hi):
            return True, f"range-{int(lo)}-{int(hi)}yr"
        if lo > TARGET_MAX_YR:
            return False, f"too-old-{int(lo)}+"
        return False, f"too-young-max-{int(hi)}"

    m = _YR_PLUS.search(s)
    if m:
        lo = float(m.group(1))
        if lo <= TARGET_MAX_YR:
            return True, f"open-{int(lo)}+"
        return False, f"too-old-{int(lo)}+"

    m = _MONTHS_ONLY.search(s)
    if m:
        months = int(m.group(1))
        years = months / 12.0
        # Only matched a months figure — treat as "up to N months" ceiling,
        # which is only OK if it clears our floor (12mo = 1yr).
        if years >= TARGET_MIN_YR:
            return True, f"months-{months}mo"
        return False, f"babies-only-{months}mo"

    if _TODDLER.search(s):
        return True, "toddler"

    if _PRESCHOOL.search(s):
        # Preschool ~3-5. Overlaps our upper bound.
        return True, "preschool"

    if _BABY_INFANT.search(s):
        # Baby/infant with no other qualifier: exclude.
        return False, "babies-only"

    # Nothing recognized — permissive. QA field will show 'unrecognized' so we
    # can revisit if it's a common source pattern we should teach.
    return True, "unrecognized"
