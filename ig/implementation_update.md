# Main site bookmark rota implementation update plan

Scope: main landing page bookmark rota integration only.  
Excluded: Dragon Hoard (`hoard/`) implementation.

For a website-repo Cursor session (frinjee.github.io / jenhammond.me), use [website_bookmark_rota_handoff.md](website_bookmark_rota_handoff.md).

## goal

Replace hard-coded bookmark rota entries on the main page with generated data from the canonical bookmark pipeline, while preserving the current visual style and CSS naming conventions.

## target contract

Primary feed for site rendering:

- `assets/json/bookmarks_rota.json`

Suggested schema:

```json
[
  {
    "bookmark_id": "d4d1f3c9b2a1e8f0",
    "title": "Example bookmark",
    "url": "https://example.com",
    "hash": "0f7ce75d13e2",
    "display_week": "2026-W33",
    "display_date": "2026-08-10",
    "taxonomy_category": "INFSEC",
    "taxonomy_subcategory": "OSINT",
    "tags": ["INFSEC", "OSINT", "SEARCH"],
    "note": ""
  }
]
```

Data source:

- generated from `out/rotation_weekly.json`
- enriched from `out/bookmark_catalog.json`

## implementation sequence

### 1) add feed generation step

1. Add a post-pipeline transform script that writes `assets/json/bookmarks_rota.json`.
2. Keep export deterministic:
   - stable key order
   - stable item ordering
   - UTF-8 + newline at EOF

### 2) update main page rendering

1. Keep existing HTML container and class conventions:
   - preserve `bookmark-rota-*` classes from current stylesheet assumptions.
2. Replace static list items with JS-rendered entries from `assets/json/bookmarks_rota.json`.
3. Add resilient behavior:
   - if feed load fails, show a compact fallback message and keep layout intact.

### 3) visibility and safety filters

1. Frontend should only render entries already filtered to `PUBLIC`.
2. Never render `REVIEW` or `PRIVATE` bookmarks.
3. Optional: show category chips (`INFSEC`, `DEV`, etc.) only when present.

### 4) deployment/update flow

Weekly flow:

1. Run pipeline (`bookmark_pipeline`) with the target Monday `--run-date` (no `--dry-run` on production Mondays).
2. Optional limited health check: `python -m bookmark_pipeline.link_health --db out/bookmarks.db --limit 50 --no-mark-inactive`
3. Back up previous feed: `assets/json/bookmarks_rota.prev.json`
4. Generate and validate `assets/json/bookmarks_rota.json` via `rota_feed build --validate`
5. Copy **only** that JSON into the website repo (`assets/json/bookmarks_rota.json` on `frinjee.github.io` by default).
6. Smoke-check bookmark rota section on desktop and mobile widths.

## quality gates

1. `bookmarks_rota.json` has exactly 12 items for normal weekly runs.
2. Each item has unique `bookmark_id` and unique `hash` in the same week.
3. Every URL is absolute and starts with `http://` or `https://`.
4. Main page still renders correctly if one item is malformed.

## phase 2 planning packet (post-phase-1 build)

Use this packet to start Phase 2 planning without writing new Phase 2 code yet.

### validated data-contract boundary

- Rotation input: `out/rotation_weekly.json`
  - required: `bookmark_id`, `title`, `hash`, `display_week`, `display_date`
- Catalog input: `out/bookmark_catalog.json`
  - required for enrichment: `bookmark_id`, `url`, `visibility_flag`, taxonomy fields, `tags`
- Feed output: `assets/json/bookmarks_rota.json`
  - built via `python -m bookmark_pipeline.rota_feed build --rotation out/rotation_weekly.json --catalog out/bookmark_catalog.json --output assets/json/bookmarks_rota.json`

### link-health prerequisites and cadence

- Install health extras: `pip install -e ".[health]"`
- Primary command: `python -m bookmark_pipeline.link_health --db out/bookmarks.db`
- Planning cadence recommendation:
  - weekly limited scan during rota build (`--limit` for quick feedback)
  - full scan before monthly cleanup decisions

### phase 2 kickoff decisions (locked)

1. `UNSORTED` threshold for hard diversity gating:
   - keep diversity checks as advisory until `UNSORTED <= 55%` of catalog.
   - once at or below `55%`, promote category-diversity checks to hard weekly gate.
2. Feed generation enforcement mode:
   - run weekly feed generation in local workflow now.
   - add CI enforcement as a Phase 2 milestone after first stable month of local runs.
3. Dead-link handling policy:
   - default to review-first (`--no-mark-inactive`) during weekly cadence.
   - apply immediate inactive marking only in scheduled cleanup runs after manual review.
4. Category quota timing:
   - introduce category-aware quotas in the first Phase 2 implementation slice.

## rollback strategy

1. Keep previous week feed as `assets/json/bookmarks_rota.prev.json`.
2. If deployment breaks:
   - swap back to previous feed
   - rerun transform with prior known-good `rotation_weekly.json`
3. If render script fails:
   - temporarily fall back to static hard-coded list while preserving CSS selectors.

## follow-up enhancements

1. Add category-aware weekly quotas for better variety.
2. Add optional weighting by low historical display count.
3. Add dead-link exclusion before final feed export.
4. Add CI check that validates schema and uniqueness before deploy.
