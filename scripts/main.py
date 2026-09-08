"""Little DMV pipeline orchestrator.

Reads sources.yaml, pulls from each iCal source and each configured HTML
scraper, normalizes → filters → dedupes, and writes data/events.json.

Run:
    python -m scripts.main                     # normal weekly refresh
    python -m scripts.main --dry-run           # print the JSON to stdout
    python -m scripts.main --only butlers-orchard
    python -m scripts.main --keep-dummy        # merge with existing dummy data

Env:
    HOME_LAT, HOME_LNG   — reference coords for distance banding (Secrets in CI)
    LOOKAHEAD_DAYS       — override the default 21-day horizon
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import ical_fetch, normalize, seasonal, weather

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "scripts" / "sources.yaml"
EVENTS_FILE = ROOT / "data" / "events.json"
SCHEMA_VERSION = 1


def load_sources() -> dict:
    with SOURCES_FILE.open() as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("ical", [])
    data.setdefault("scrape", [])
    return data


def _ical_source_from(raw: dict) -> ical_fetch.ICalSource:
    return ical_fetch.ICalSource(
        id=raw["id"],
        name=raw.get("name", raw["id"]),
        url=raw["url"],
        venue_default=raw.get("venue_default", ""),
        place_default=raw.get("place_default", "indoor"),
        distance_venue_key=raw.get("distance_venue_key"),
        source=raw.get("source", raw["id"]),
    )


def _stamp_source_flags(raws: list[dict], src: dict) -> None:
    """Copy per-source config flags onto every raw event from that source so
    downstream normalize/filter can act on them without knowing sources.yaml.
    """
    if src.get("require_kid_signal"):
        for e in raws:
            e["_require_kid_signal"] = True


def run_ical(sources: list[dict], only: set[str] | None,
             health: dict[str, dict]) -> tuple[list[dict], list[str]]:
    raws: list[dict] = []
    errors: list[str] = []
    for src in sources:
        if only and src["id"] not in only:
            continue
        try:
            got = ical_fetch.fetch(_ical_source_from(src))
            _stamp_source_flags(got, src)
            raws.extend(got)
            _mark_ok(health, src["id"], len(got))
            print(f"  iCal {src['id']}: {len(got)} events", file=sys.stderr)
        except Exception as exc:
            errors.append(f"iCal {src['id']}: {exc}")
            _mark_error(health, src["id"], str(exc))
            print(f"  iCal {src['id']}: FAILED — {exc}", file=sys.stderr)
    return raws, errors


def run_scrapers(scrapers: list[dict], only: set[str] | None,
                 health: dict[str, dict]) -> tuple[list[dict], list[str]]:
    raws: list[dict] = []
    errors: list[str] = []
    for entry in scrapers:
        if only and entry["id"] not in only:
            continue
        try:
            mod = importlib.import_module(entry["module"])
            got = mod.fetch()
            for e in got:
                e.setdefault("source", entry["id"])
            _stamp_source_flags(got, entry)
            raws.extend(got)
            _mark_ok(health, entry["id"], len(got))
            print(f"  scrape {entry['id']}: {len(got)} events", file=sys.stderr)
        except Exception as exc:
            errors.append(f"scrape {entry['id']}: {exc}")
            _mark_error(health, entry["id"], str(exc))
            print(f"  scrape {entry['id']}: FAILED — {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
    return raws, errors


def _load_prev_health() -> dict[str, dict]:
    if not EVENTS_FILE.exists():
        return {}
    try:
        with EVENTS_FILE.open() as f:
            return (json.load(f) or {}).get("sources", {}) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def _mark_ok(health: dict[str, dict], source_id: str, count: int) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    entry = health.setdefault(source_id, {})
    entry["last_success_at"] = now
    entry["last_count"] = count
    entry["last_error"] = None


def _mark_error(health: dict[str, dict], source_id: str, msg: str) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    entry = health.setdefault(source_id, {})
    entry["last_error_at"] = now
    # last_success_at is deliberately left alone — Em wants "how long since it
    # last worked" more than "when did it most recently break."
    entry["last_error"] = msg[:500]


def dedupe(events: list[dict]) -> list[dict]:
    """Keep the first occurrence of each (date, name, venue) tuple. Sources
    listed earlier in sources.yaml win — put canonical iCal feeds ahead of
    aggregator scrapes.
    """
    seen: set[tuple[str, str, str]] = set()
    out: list[dict] = []
    for e in events:
        key = (e["date"], e["name"].strip().lower(), (e["venue"] or "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print JSON to stdout, don't write")
    ap.add_argument("--only", help="comma-separated source ids to run", default=None)
    ap.add_argument("--keep-dummy", action="store_true",
                    help="merge with existing events.json (keeps manual/dummy events)")
    args = ap.parse_args()

    only = set(args.only.split(",")) if args.only else None

    if os.environ.get("LOOKAHEAD_DAYS"):
        ical_fetch.LOOKAHEAD_DAYS = int(os.environ["LOOKAHEAD_DAYS"])

    print("Little DMV refresh starting…", file=sys.stderr)
    sources = load_sources()
    print(f"  configured: {len(sources['ical'])} iCal, {len(sources['scrape'])} scrapers",
          file=sys.stderr)

    raws: list[dict] = []
    health = _load_prev_health()  # start from previous state; each run updates it
    ical_raws, ical_errs = run_ical(sources["ical"], only, health)
    raws.extend(ical_raws)
    scrape_raws, scrape_errs = run_scrapers(sources["scrape"], only, health)
    raws.extend(scrape_raws)

    if only is None or "seasonal" in only:
        try:
            seasonal_raws = seasonal.load()
            raws.extend(seasonal_raws)
            _mark_ok(health, "seasonal", len(seasonal_raws))
            print(f"  seasonal: {len(seasonal_raws)} events", file=sys.stderr)
        except Exception as exc:
            print(f"  seasonal: FAILED — {exc}", file=sys.stderr)
            _mark_error(health, "seasonal", str(exc))
            ical_errs.append(f"seasonal: {exc}")

    now = datetime.now(timezone.utc)
    events = [normalize.to_canonical(r, now=now) for r in raws]
    events = [e for e in events if e is not None]
    print(f"  after normalize + age filter: {len(events)} events", file=sys.stderr)

    events = dedupe(events)
    print(f"  after dedupe: {len(events)} events", file=sys.stderr)

    # Stamp outdoor events with NWS forecast (no-op if HOME_LAT/LNG unset).
    forecast_map = weather.build_forecast_map()
    weather.stamp(events, forecast_map)

    if args.keep_dummy and EVENTS_FILE.exists():
        with EVENTS_FILE.open() as f:
            prev = json.load(f)
        prev_events = [e for e in prev.get("events", []) if e.get("source") == "manual"]
        # Manual events come first so scraper duplicates lose to them.
        events = dedupe(prev_events + events)
        print(f"  after merging {len(prev_events)} manual events: {len(events)} total",
              file=sys.stderr)

    events.sort(key=lambda e: (e["date"], e["time"], e["name"]))

    payload = {
        "last_updated": now.isoformat().replace("+00:00", "Z"),
        "schema_version": SCHEMA_VERSION,
        "sources": health,
        "events": events,
    }

    if args.dry_run:
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with EVENTS_FILE.open("w") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")
        print(f"  wrote {EVENTS_FILE.relative_to(ROOT)}", file=sys.stderr)

    if ical_errs or scrape_errs:
        print("\nErrors:", file=sys.stderr)
        for e in ical_errs + scrape_errs:
            # ::warning:: is a GitHub Actions annotation — shows in the workflow
            # summary and on the commit page without failing the job. Em sees
            # the flake without losing the successful sources.
            print(f"::warning title=Source failed::{e}")
            print(f"  - {e}", file=sys.stderr)

    # Exit code contract:
    #   0  — at least one event was written (partial success is still success)
    #   1  — everything failed AND we had at least one configured source
    #   0  — no sources configured at all (empty registry is a valid state)
    total_configured = len(sources["ical"]) + len(sources["scrape"])
    if total_configured > 0 and not events:
        print("::error::All sources failed and no events were written.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
