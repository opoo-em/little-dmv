# National Children's Museum - output below

I fetched the events page and an individual event page, but I should flag something important before the code: this site (Next.js + Sanity) renders its event list and calendar client-side — the raw server HTML I could inspect had an empty "all events" section, and the per-event calendar ("Select a date to see the time") only shows highlighted/clickable days once JS runs. I could not find `<script type="application/ld+json">` Event nodes in what I could see, and I have no way to execute JS or inspect the actual embedded data blob directly.

What I could verify reliably:

* Individual event pages (`/explore/events/<slug>`) are server-rendered with a consistent structure: `<h1>` title, an "about" section with the description, and a "details" section with a location-icon → venue and an ages-icon → age hint.
* These pages are also indexed by Google with real descriptions, confirming they're not fully client-only.
* No sitemap.xml link surfaced in search, though I coded a sitemap check anyway since it's a common, cheap discovery path.

So the scraper below layers several strategies and degrades gracefully instead of guessing: JSON-LD first (works immediately if present, per your instructions), then link/sitemap discovery of event pages, then structural HTML parsing for name/description/venue/age (which I did verify), then a cascade of heuristics for the actual date/time data (`<time>` elements → date-ish data attributes → embedded JSON script blobs → a defensive calendar-table reader that only trusts leaf day-cells marked interactive). That last piece is the one most likely to need a tweak once you run it against the live JS-free HTML — if it comes back empty, share me a saved copy of one event page's HTML and I'll tighten it to the real markup.

*Code landed at `scripts/scrapers/national_childrens_museum.py`.*

## Post-delivery note

If the date-heuristic cascade in step 4 comes back empty on a real run (likely, given how JS-driven that calendar is), the cheapest next move is probably to open the site in a real browser's devtools Network tab and see what endpoint the calendar actually calls when you pick a date — that'll almost certainly beat further blind heuristics on my end.
