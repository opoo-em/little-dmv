"""Content filter — adult-signal blocklist and kid-signal requirement.

Locks the rules that keep Rockville-city commission meetings, adult concerts,
and naloxone trainings out of a toddler mom's dashboard.
"""

from __future__ import annotations

import pytest

from scripts.filter import content_passes, has_adult_signal, has_kid_signal


# Real event titles pulled from Rockville-city output on 2026-09-06.
# These have unambiguous adult signals and should be rejected everywhere.
REAL_ROCKVILLE_ADULT = [
    "Planning Commission Meeting",
    "Cultural Arts Commission Meeting",
    "Mayor and Council Meeting",
    "Human Services Advisory Commission Meeting",
    "Commission on Aging Meeting",
    "Rockville Pedestrian Advocacy Committee Meeting",
    "Rockville Goes Purple: Community Naloxone Training",
    "Rockville Goes Purple: Nonprofit Lunch and Learn",
    "City Holiday: Labor Day",
    "Sept. 11 Remembrance Ceremony",
    "Victorian Lyric Opera Company Presents Haddon Hall",
]

# Adult-flavored events that DON'T match a hard signal but should still be
# excluded from firehose sources because they carry no kid signal.
REAL_ROCKVILLE_ADULT_SOFT = [
    ("ArmEvents Presents: An Evening of Elegance and Virtuosity Live Concert",
     "Grammy-Nominated Pianist. World-Class Violin Virtuoso."),
    ("Art Exhibition Opens: The World As We View It",
     "Explore a new exhibition by the Montpelier Printmakers."),
]

# Real kid-friendly Rockville events from the same run.
REAL_ROCKVILLE_KID = [
    ("Little Sprouts", "Designed especially for our youngest naturalists, "
                        "this toddler program introduces children to nature."),
    ("Gentle Explorers", "Designed for young children and their caregivers, "
                         "this nature program encourages slowing down."),
    ("2026 Taiwan Bubble Tea Festival", "Family festival with music and food."),
]


@pytest.mark.parametrize("name", REAL_ROCKVILLE_ADULT)
def test_adult_signal_rejects_muni_junk(name):
    assert has_adult_signal(name, "")
    assert not content_passes(name, "", require_kid_signal=True)
    assert not content_passes(name, "", require_kid_signal=False)


@pytest.mark.parametrize("name,desc", REAL_ROCKVILLE_ADULT_SOFT)
def test_soft_adult_rejected_only_when_kid_signal_required(name, desc):
    # These aren't hard adult signals — a non-firehose source would keep them.
    assert content_passes(name, desc, require_kid_signal=False)
    # But firehose sources (Rockville, Kennedy Center) require kid signal.
    assert not content_passes(name, desc, require_kid_signal=True)


@pytest.mark.parametrize("name,desc", REAL_ROCKVILLE_KID)
def test_kid_signal_keeps_toddler_programs(name, desc):
    assert not has_adult_signal(name, desc)
    assert has_kid_signal(name, desc)
    assert content_passes(name, desc, require_kid_signal=True)


def test_kid_signal_in_description_is_enough():
    assert content_passes(
        "Special Event",
        "This event is designed for toddlers and their caregivers.",
        require_kid_signal=True,
    )


def test_unspecified_without_kid_signal_rejected_when_required():
    assert not content_passes(
        "Concert in the Park",
        "Come enjoy live music on the lawn.",
        require_kid_signal=True,
    )


def test_unspecified_without_kid_signal_kept_by_default():
    # Non-firehose source: keep permissively.
    assert content_passes(
        "Concert in the Park",
        "Come enjoy live music on the lawn.",
        require_kid_signal=False,
    )


def test_adult_signal_wins_over_kid_signal():
    # Even if a muni meeting mentions "children" in the description, the
    # meeting itself is not a toddler event.
    assert not content_passes(
        "Planning Commission Meeting",
        "Agenda item includes proposed children's playground grant.",
        require_kid_signal=True,
    )


def test_adult_only_marker():
    assert has_adult_signal("Wine Tasting Fundraiser", "Ages 21+ only.")
    assert not content_passes("Wine Tasting Fundraiser", "Ages 21+ only.")


def test_various_kid_signals():
    assert has_kid_signal("Baby Storytime", "")
    assert has_kid_signal("Preschool Playgroup", "")
    assert has_kid_signal("Family Nature Walk", "")
    assert has_kid_signal("Music Together", "For infants and toddlers.")
    assert has_kid_signal("Mommy and Me Yoga", "")
    assert has_kid_signal("", "Ages 2-4 welcome.")
    assert has_kid_signal("Fall Festival", "")


def test_no_kid_signal():
    assert not has_kid_signal("Board Meeting", "Monthly board meeting.")
    assert not has_kid_signal("Art Exhibition Opening", "New gallery show.")
