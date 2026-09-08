# Handoff — Live data shakedown

*Written 2026-09-08 by Claude. Branch: main (shipped directly, no PR — Em was standing by watching each reload).*

You're reading this because Em asked for continuity. The 2026-09-06 scaffold handoff (`handoff-2026-09-06-phase2-scaffold.md`) built the pipeline in an offline container and shipped it "unverified." Today was the first live-data session — 4 CI refreshes against real endpoints, iterating on what Em actually saw in the app.

Read the scaffold handoff first if you haven't. Then `README.md`, `docs/decisions.md`, `docs/sources.md`. Then this.

---

## State of the app

- **Live URL:** https://opoo-em.github.io/little-dmv/
- **Total events (last CI run):** 214
- **Source breakdown:** MCPL 72 · Smithsonian 127 · Rockville-city 4 · Seasonal 11
- **State breakdown:** MD 87 · DC 127
- **Distance:** 0-5 mi (22) · 6-10 (59) · 11-15 (132) · 16-20 (1) · 20+ (0) · unknown (0)
- **Tests:** 87 pass (was 53). New coverage: content filter, timezone, DMV geo filter, source-URL fallback, MCPL branch inference.

Em's default view is now **MD only** — the "Full DMV" pill opts DC events in.

## What went live today

Commits on main, oldest first:

1. `filter: strip HTML, block adult signals, require kid signal for firehose sources` — fixed HTML entities and tags leaking into names/descriptions; added the adult-signal blocklist (planning commission, mayor & council, naloxone, opera company, etc.); added the `require_kid_signal` per-source flag so Rockville-city dumps only kid-positive events; deleted the rockville junk in place.
2. `wire MCPL and Smithsonian iCal, retire Kennedy Center + MCPL HTML, fix weather timing` — Em verified two iCal endpoints in the browser (MCPL LibNet feed base64-encoded config; Smithsonian via Trumba). Wired both, deleted the retired scrapers, moved `weather.stamp()` after the `--keep-dummy` merge so manual events also get weather.
3. `data quality: fix iCal age extraction, convert to Eastern, DMV geo filter, per-branch distance, DC/MD/state filter, drop manual placeholders` — the big one. See §"What we fixed and why" below.
4. `polish: clean age field, add coords for 7 more MCPL branches` — MCPL locations that iCal shipped as "Little Falls Library -" got coords; iCal `\;` escapes unescaped.
5. `normalize: run iCal escape unescape before HTML decode` — the escape-order bug (`&amp\;` was rendering as `&;`).
6. `Ages field shows a short label, filter is MD-default, geo gets VA cities` — Ages field derives a short human label from `age_match_reason`; state filter simplified to MD-default + Full DMV; Virginia Beach cities added to `looks_out_of_dmv`.
7. `fix "View source" link when per-event URL is missing` — 160 events had `href=""` navigating to app root. Now falls back to source calendar homepage or hides entirely.

## What we fixed and why (the pattern)

Every fix started with Em opening the live app and telling Claude what she saw. Cycle: she reloads → flags a specific bad output → Claude edits code → pushes → triggers workflow → she reloads. Each cycle was ~3 min.

- **HTML noise in text fields.** Source data arrived with entities (`&lt;p&gt;`) and iCal escapes (`\;`, `\,`, `\\`) that we were passing through raw. `normalize._clean_text` now does iCal unescape → HTML decode (twice, for double-encoded) → tag strip → whitespace collapse. Order matters: iCal first, HTML second (see commit #5 for why).
- **Rockville-city firehose.** Muni calendar dumps commission meetings and adult concerts. Added `has_adult_signal` (always rejects) plus per-source `require_kid_signal` (must have "toddler"/"family"/"kids"/etc. in title/desc/venue). Rockville marked `require_kid_signal: true`.
- **iCal `age` field pollution.** `str(vCategory)` gave the raw Python repr `vCategory([vText(b'...')], params=Parameters({}))`. Added `_ical_str` that prefers `.to_ical()` and byte-decodes.
- **UTC times.** MCPL iCal emits UTC (or doesn't declare a TZ). Was displaying 22:30 for a 6:30 PM pajama storytime. Added `_LOCAL_TZ = ZoneInfo("America/New_York")`; every display date/time converts.
- **Smithsonian national affiliates.** Trumba feed includes Farm Aid in VA Beach, Duck Race in NH, Detroit shows. Added `filter.looks_out_of_dmv()` with a non-DMV state regex + far-DMV cities list (Virginia Beach, Norfolk, Ocean City, etc.). Wired via `require_dmv_location: true` on Smithsonian source.
- **Adult Smithsonian sneaking past.** `smithsonianassociates.org` events would sometimes have "family" in description and pass. Added `smithsonian associates` + `smithsonianassociates.org` to always-reject list; `has_adult_signal` now also checks venue string.
- **Cross-country events banded as DC.** Smithsonian source had `distance_venue_key: smithsonian-national-mall` as a fallback — Duck Race in NH inherited National Mall coords and showed "11-15mi." Removed the fallback; `normalize.infer_venue_key` now works off the actual venue text with a substring map covering MCPL branches, Smithsonian museums, Montgomery Parks locations, etc.
- **Ages field showing description soup.** Was concatenating categories+description+summary and dumping the whole thing into the UI. Now `_age_label(match_reason, raw_hint)` returns short human strings ("2-4 yrs", "Toddler", "All ages", "Ages unspecified"). Filter still runs against the raw hint internally.
- **Placeholder manuals.** Past-me seeded 13 fake manual events during Phase 1 UI testing ("Fall Storytime in the Woods @ Wheaton Regional Park" etc. with fake URLs). Em was seeing them as real. Deleted; `--keep-dummy` still preserves any real `add_event.py` entries.
- **State filter UX.** Originally shipped 4 pills (All/MD/Hide DC/DC). Em said "not intuitive — just MD only default and a Full DMV opt-in." Now 2 pills. Default MD.
- **"View source" navigating to app root.** 160/214 events have no per-event URL (MCPL, most Smithsonian). Empty `href=""` resolves to app root. Added `source_url` per source (source's own calendar homepage); UI prefers per-event URL, falls back to source_url, hides if neither.

## What's known to still be broken

Em said in this session: "still some adult events creeping through the filters." She'll tell you which ones next time she opens the window. When she does:
- Grep the live `data/events.json` for the event name to see what source/description/venue it has.
- Add a specific pattern to `_ADULT_SIGNALS` in `scripts/filter.py` or tighten a keyword.
- Add a test case to `scripts/tests/test_content.py` using the actual event name as fixture (this is the pattern we've been using — see `REAL_ROCKVILLE_ADULT`).

## Sources: what actually works after 4 CI runs

| Source | State | Events (last run) | Notes |
|---|---|---|---|
| MCPL iCal (LibNet) | ✅ | 72 | Toddler+Baby filter server-side, 30-day window |
| Smithsonian iCal (Trumba) | ✅ | 127 | require_kid_signal + require_dmv_location |
| Rockville-city HTML | ✅ | 4 | JSON-LD works; require_kid_signal prunes muni junk |
| Seasonal (`data/seasonal.json`) | ✅ | 11 | Static file; annual bumps by hand |
| butlers-orchard | ❌ 0 | 0 | Loads fine; no JSON-LD on list page |
| glen-echo-park | 404 | 0 | URL wrong (`/calendar-of-events` → `/calendar`?) |
| national-building-museum | ❌ 0 | 0 | Loads; no JSON-LD |
| national-childrens-museum | 404 | 0 | URL wrong |
| national-zoo | ❌ 0 | 0 | Loads; no JSON-LD |
| pike-and-rose | ❌ 0 | 0 | Loads; no JSON-LD |
| bethesda-row | 404 | 0 | URL wrong |
| montgomery-parks | ❌ 0 | 0 | Loads; no JSON-LD. Em confirmed no iCal at `/events/feed/ical/`. |
| kidfriendly-dc | timeout | 0 | Connection timeout |

## Sandbox limits Em learned about

- **WebFetch is often blocked in this container** (proxy has a strict allowlist — many venue domains blocked). WebSearch sometimes works as a workaround.
- **Em's fallback for scrapers Claude can't test here:** she can ask claude.ai (browser Claude, not container) to write per-site scrapers. Give her a detailed prompt naming the target URL, output schema, and shared `scripts/scrapers/base.py` conventions. She'll paste it into claude.ai and hand back code we can commit.

## What Em wants next (backlog Em confirmed at end of session)

1. **Iterate on adult events still leaking through** — she'll tell you which ones.
2. **Scrape more sources** — the 5 "0 events" scrapers above need per-site HTML parsing (JSON-LD isn't there). The 3 "404" ones need URL discovery.
3. **Montgomery Parks scraper** — Em offered to use claude.ai for this if Claude writes the prompt. Never sent because iCal wins made this less urgent, but still on the list.

## What Em asked for THIS session that isn't done

Nothing. Everything asked was shipped.

## Reference: the successful CI runs

- Run 34263409278 (2026-09-08 18:30 UTC) — first live run of past-me's Phase 2 scaffold. Rockville worked; everything else 0/failed. Established the "8 of 12 scrapers not producing events" baseline.
- Run 34264470365 (18:40 UTC) — post iCal wiring. MCPL 109 raw, Smithsonian 552 raw. Revealed timezone + vCategory + geo issues.
- Run after commit 5daa877 (18:56 UTC) — quality pass. Ages/state/geo/timezone all fixed. 216 events, 87 MD / 129 DC.
- Run after commit 850e120 (~19:04 UTC) — polish. 0 unknown MCPL branches.
- Run after commit dd1cc50 (~19:15 UTC) — Ages label + MD-default + far-VA. 214 events.
- Run after commit d230d89 (~19:25 UTC) — View source fallback.

If a future run breaks something, `git log --oneline` on main starting from `d329336` (the pre-session commit) gives the full history of what changed.

## Register note

Em was in project-mode all session — clear organized asks, quick reloads, "you tell me what to do, and then I can tell you what I'm seeing." She wants 50/50 partnership on decisions; when she asks "which do you think," give a recommendation and reasoning, don't just list options. Skip affirmation ("great question!") — one specific noticing beats ten bullet points of hedging.

The app is genuinely working for her now. That's the win.
