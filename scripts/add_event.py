"""Manual event add — for the 'I saw a sign for X' flow.

Usage
-----
Interactive prompts:
    python -m scripts.add_event

JSON on stdin:
    echo '{"name":"...","date":"YYYY-MM-DD","time":"HH:MM","venue":"...","url":"..."}' \
        | python -m scripts.add_event --stdin

CLI flags (for Claude to add from chat with one line):
    python -m scripts.add_event \
        --name "Congressional Plaza Pumpkin Painting" \
        --date 2026-10-13 --time 14:00 --end 16:00 \
        --venue "Congressional Plaza" --venue-key congressional-plaza \
        --place outdoor --cost free --cost-label "Free" \
        --age "All ages" --url https://congressionalplaza.com/ \
        --description "Pumpkin painting on the plaza."

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


def from_args(args) -> dict:
    date = args.date
    time = args.time or "10:00"
    end = args.end
    start = datetime.fromisoformat(f"{date}T{time}").replace(tzinfo=timezone.utc)
    end_dt = None
    if end:
        end_dt = datetime.fromisoformat(f"{date}T{end}").replace(tzinfo=timezone.utc)
    return {
        "name": args.name,
        "start": start,
        "end": end_dt,
        "venue": args.venue or "",
        "venue_key": args.venue_key or None,
        "place": args.place or "indoor",
        "cost_type": args.cost or "free",
        "cost_label": args.cost_label or ("Free" if (args.cost or "free") == "free" else ""),
        "age": args.age or "All ages",
        "url": args.url or "",
        "description": args.description or "",
        "source": "manual",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdin", action="store_true", help="read JSON blob from stdin")
    ap.add_argument("--name", help="event name")
    ap.add_argument("--date", help="YYYY-MM-DD")
    ap.add_argument("--time", help="HH:MM (default 10:00)")
    ap.add_argument("--end", help="HH:MM end time")
    ap.add_argument("--venue")
    ap.add_argument("--venue-key", dest="venue_key",
                    help="see scripts/distance.py VENUE_COORDS")
    ap.add_argument("--place", choices=["indoor", "outdoor"])
    ap.add_argument("--cost", choices=["free", "paid"])
    ap.add_argument("--cost-label", dest="cost_label")
    ap.add_argument("--age", help="age string, e.g. 'All ages', '0-3 yrs', 'toddler'")
    ap.add_argument("--url")
    ap.add_argument("--description")
    args = ap.parse_args()

    if args.stdin:
        raw = from_stdin()
    elif args.name and args.date:
        raw = from_args(args)
    else:
        raw = interactive()
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
