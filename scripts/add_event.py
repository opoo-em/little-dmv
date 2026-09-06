"""Manual event add — for the 'I saw a sign for X' flow.

Usage (interactive):
    python -m scripts.add_event

Or non-interactively with a JSON blob on stdin:
    echo '{"name":"...","date":"YYYY-MM-DD","time":"HH:MM","venue":"...","url":"..."}' \
        | python -m scripts.add_event --stdin

Manual events carry source='manual' and survive `main.py --keep-dummy` refreshes.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import distance, normalize

EVENTS_FILE = Path(__file__).resolve().parent.parent / "data" / "events.json"


def prompt(label: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    val = input(f"{label}{hint}: ").strip()
    return val or default


def interactive() -> dict:
    name = prompt("Event name")
    date = prompt("Date (YYYY-MM-DD)")
    time = prompt("Time (HH:MM)", "10:00")
    end = prompt("End time (HH:MM, blank for none)")
    venue = prompt("Venue name")
    venue_key = prompt("Distance venue key (see scripts/distance.py)", "")
    place = prompt("Place (indoor/outdoor)", "indoor")
    cost_type = prompt("Cost (free/paid)", "free")
    cost_label = prompt("Cost label", "Free" if cost_type == "free" else "$")
    age = prompt("Age string (e.g. '0-3 yrs', 'All ages', 'toddler')", "All ages")
    url = prompt("Source URL", "")
    description = prompt("Description (one line)", "")

    start = datetime.fromisoformat(f"{date}T{time}").replace(tzinfo=timezone.utc)
    end_dt = None
    if end:
        end_dt = datetime.fromisoformat(f"{date}T{end}").replace(tzinfo=timezone.utc)

    return {
        "name": name,
        "start": start,
        "end": end_dt,
        "venue": venue,
        "venue_key": venue_key or None,
        "place": place,
        "cost_type": cost_type,
        "cost_label": cost_label,
        "age": age,
        "url": url,
        "description": description,
        "source": "manual",
    }


def from_stdin() -> dict:
    raw = json.load(sys.stdin)
    date = raw["date"]
    time = raw.get("time", "10:00")
    end = raw.get("end")
    raw["start"] = datetime.fromisoformat(f"{date}T{time}").replace(tzinfo=timezone.utc)
    raw["end"] = (
        datetime.fromisoformat(f"{date}T{end}").replace(tzinfo=timezone.utc)
        if end else None
    )
    raw.setdefault("source", "manual")
    return raw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdin", action="store_true")
    args = ap.parse_args()

    raw = from_stdin() if args.stdin else interactive()
    event = normalize.to_canonical(raw)
    if event is None:
        print("Rejected (missing required fields or failed age filter).", file=sys.stderr)
        return 1

    with EVENTS_FILE.open() as f:
        data = json.load(f)
    data.setdefault("events", []).append(event)
    data["events"].sort(key=lambda e: (e["date"], e["time"], e["name"]))
    data["last_updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with EVENTS_FILE.open("w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"Added: {event['name']} on {event['date']} @ {event['time']} — {event['venue']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
