"""Filters for the pipeline.

Two independent gates:

- `age_passes(raw_age_string)` — keep events whose age range overlaps
  ~1-3 years (Felix's range). Permissive on unrecognized strings.

- `content_passes(name, description, require_kid_signal)` — reject events
  whose title/description carries an unambiguous adult-only signal
  (municipal meetings, adult concerts, adult training). When
  `require_kid_signal=True` (set per-source in sources.yaml for firehose
  feeds like Rockville city calendar), also require a positive kid signal
  in the title/description.

Both return a (passes, reason) shape for QA visibility.
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


# =============================================================================
# Content filter — adult-signal blocklist + kid-signal detector
# =============================================================================

# Patterns whose presence in the title or description means "not for a toddler,
# reject regardless of source." Keep this list tight and high-precision — the
# cost of a false positive is losing a real kid event.
_ADULT_SIGNALS = [
    # Municipal governance
    re.compile(r"\bplanning\s+commission\b", re.I),
    re.compile(r"\bcity\s+council\b", re.I),
    re.compile(r"\bmayor\s+(?:and|&)\s+council\b", re.I),
    re.compile(r"\bcouncil\s+meeting\b", re.I),
    re.compile(r"\bcommission\s+meeting\b", re.I),
    re.compile(r"\badvisory\s+(?:committee|commission|board)\b", re.I),
    re.compile(r"\badvocacy\s+committee\b", re.I),
    re.compile(r"\bcultural\s+arts\s+commission\b", re.I),
    re.compile(r"\bcommission\s+on\s+aging\b", re.I),
    re.compile(r"\bhuman\s+services\s+advisory\b", re.I),
    re.compile(r"\bpedestrian\s+advisory\b", re.I),
    re.compile(r"\bboard\s+meeting\b", re.I),
    re.compile(r"\bcity\s+holiday\b", re.I),
    re.compile(r"\bpublic\s+hearing\b", re.I),
    # Adult content / trainings
    re.compile(r"\bnaloxone\b", re.I),
    re.compile(r"\bnarcan\b", re.I),
    re.compile(r"\blunch\s+and\s+learn\b", re.I),
    re.compile(r"\bnetworking\b", re.I),
    re.compile(r"\bhappy\s+hour\b", re.I),
    re.compile(r"\bwine\s+tasting\b", re.I),
    re.compile(r"\bbeer\s+garden\b", re.I),
    re.compile(r"\bfundraiser\s+gala\b", re.I),
    re.compile(r"\bcareer\s+fair\b", re.I),
    re.compile(r"\bjob\s+fair\b", re.I),
    re.compile(r"\bremembrance\s+ceremony\b", re.I),
    # Adult-only markers
    re.compile(r"\b(?:18|21)\s*\+", re.I),
    re.compile(r"\badults?\s+only\b", re.I),
    re.compile(r"\bages?\s+18\+", re.I),
    re.compile(r"\bages?\s+21\+", re.I),
    # Adult performance types (these are almost never toddler-appropriate;
    # legit kid concerts are titled "Kids Concert" and pass on the kid signal)
    re.compile(r"\bopera\s+company\b", re.I),
    re.compile(r"\bsymphony\s+orchestra\b", re.I),
    re.compile(r"\bchamber\s+music\b", re.I),
]

# Anything the title/description mentions that says "this event is for kids or
# families." Deliberately broad — false positives here just mean we KEEP an
# event that a firehose source would otherwise cut.
_KID_SIGNALS = [
    re.compile(r"\btoddler(s)?\b", re.I),
    re.compile(r"\b(baby|babies|infant(s)?|newborn(s)?)\b", re.I),
    re.compile(r"\b(kid|kids|kiddo|kiddos)\b", re.I),
    re.compile(r"\bchild(ren)?\b", re.I),
    re.compile(r"\bfamil(y|ies)\b", re.I),
    re.compile(r"\bfamily[-\s]friendly\b", re.I),
    re.compile(r"\bkid[-\s]friendly\b", re.I),
    re.compile(r"\byouth\b", re.I),
    re.compile(r"\bpre[-\s]?school(er)?\b", re.I),
    re.compile(r"\bstory[-\s]?time\b", re.I),
    re.compile(r"\bstory[-\s]?hour\b", re.I),
    re.compile(r"\bplay\s?group\b", re.I),
    re.compile(r"\ball\s+ages\b", re.I),
    re.compile(r"\bages?\s+\d", re.I),
    re.compile(r"\bsprouts?\b", re.I),
    re.compile(r"\bcaterpillars?\b", re.I),
    re.compile(r"\blittle\s+(explorers?|learners?|scientists?|artists?)\b", re.I),
    re.compile(r"\bmommy\s+(and|&)\s+me\b", re.I),
    re.compile(r"\bdaddy\s+(and|&)\s+me\b", re.I),
    re.compile(r"\bmusic\s+together\b", re.I),
    re.compile(r"\bstroller\b", re.I),
    re.compile(r"\bnature\s+program\b", re.I),
    re.compile(r"\bpetting\s+zoo\b", re.I),
    re.compile(r"\bfestival\b", re.I),  # marginal — muni festivals are usually family
]


def _matches_any(patterns, *texts) -> bool:
    for text in texts:
        if not text:
            continue
        for pat in patterns:
            if pat.search(text):
                return True
    return False


def has_adult_signal(name: str, description: str = "") -> bool:
    return _matches_any(_ADULT_SIGNALS, name, description)


def has_kid_signal(name: str, description: str = "") -> bool:
    return _matches_any(_KID_SIGNALS, name, description)


def content_passes(name: str, description: str = "",
                   require_kid_signal: bool = False) -> bool:
    """Return True if the event's title/description should be kept.

    Rules, in order:
      1. Reject if any adult-signal pattern matches. Always.
      2. If require_kid_signal is True (firehose source), require at least one
         kid-signal pattern in title or description.
      3. Otherwise keep.
    """
    if has_adult_signal(name, description):
        return False
    if require_kid_signal and not has_kid_signal(name, description):
        return False
    return True
