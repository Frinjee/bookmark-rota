# bookmark-rota

Local pipeline that ingests Chrome and Firefox bookmark DOCX exports, deduplicates and classifies them, persists a catalog in SQLite, and emits JSON/HTML rotation artifacts.

## Python environment

Requires **Python 3.11+**.

Install the package and default runtime dependencies (includes **rapidfuzz** for fuzzy dedupe):

```powershell
pip install -e .
```

Optional dependency groups:

| Extra | Purpose |
|-------|---------|
| `dev` | pytest, pytest-cov, ruff |
| `health` | httpx, tenacity — dead-link scanning |
| `schema` | jsonschema — `bookmarks_rota.json` validation |
| `llm` | openai — optional LLM taxonomy fallback hook |

Examples:

```powershell
pip install -e ".[dev]"
pip install -e ".[dev,health,schema]"
```

Phase 1 runs on the standard library plus **rapidfuzz**; no other runtime packages are required for the core pipeline.

## Privacy obfuscation for PRIVATE records

When PRIVATE bookmarks are present, set `BOOKMARK_ROTA_OBFUSCATION_KEY` before running the pipeline.
The key is used to HMAC-obfuscate PRIVATE fields in exported JSON/HTML artifacts while keeping PUBLIC
records unchanged.

```powershell
$env:BOOKMARK_ROTA_OBFUSCATION_KEY = "set-a-long-random-local-secret"
```

Operational policy:
- Do not commit the obfuscation key.
- Rotate the key quarterly (or immediately after suspected exposure).

## Generated artifacts (local only)

The `out/` directory is gitignored. Regenerate it with the pipeline; do not commit catalog, DB, or HTML exports.

Bookmark DOCX inputs under `ig/*.docx` stay local as well. Operational runbooks live in [`ig/task_plan.md`](ig/task_plan.md) and [`ig/website_bookmark_rota_handoff.md`](ig/website_bookmark_rota_handoff.md).

**If this repo was ever public with `out/` committed:** older history may still contain bookmark metadata (including URLs captured from exports). Ignoring `out/` going forward does not scrub git history. Rotate any credentials that appeared in bookmark URLs, and consider making the repo private or rewriting history to drop `out/` from past commits.

## Run pipeline

Pass an explicit Monday `--run-date` for weekly rotation. If omitted, the CLI uses today's date.

```powershell
python -m bookmark_pipeline `
  --chrome-docx ig/bookmarks_5_30_26.docx `
  --firefox-docx ig/bookmarks-ff.docx `
  --output-dir out `
  --run-date 2026-08-10
```

Use `--dry-run` to rehearse without writing display history. Production Mondays must omit `--dry-run` so history advances.

## Monday publish checklist

Each Monday, produce a validated 12-item site feed and copy only that file into the website repo.

1. Set the obfuscation key when PRIVATE records exist:

```powershell
$env:BOOKMARK_ROTA_OBFUSCATION_KEY = "set-a-long-random-local-secret"
```

2. Run the pipeline for the target Monday (no `--dry-run`):

```powershell
python -m bookmark_pipeline `
  --chrome-docx ig/bookmarks_5_30_26.docx `
  --firefox-docx ig/bookmarks-ff.docx `
  --output-dir out `
  --run-date YYYY-MM-DD
```

3. Optional limited health check (review-first; does not mark inactive):

```powershell
python -m bookmark_pipeline.link_health --db out/bookmarks.db --limit 50 --no-mark-inactive
```

4. Back up the previous site feed, then build and validate the new one (`schema` extra required for `--validate`):

```powershell
Copy-Item assets/json/bookmarks_rota.json assets/json/bookmarks_rota.prev.json -ErrorAction SilentlyContinue
python -m bookmark_pipeline.rota_feed build `
  --rotation out/rotation_weekly.json `
  --catalog out/bookmark_catalog.json `
  --output assets/json/bookmarks_rota.json `
  --validate
```

5. Confirm gates: exactly 12 items (or an intentional short week), unique `bookmark_id` / `hash` values, absolute `http(s)` URLs, and no 4chan hosts or known 4chan search/indexers (`4chan.org`, `4channel.org`, `4cdn.org`, `4chansearch.com`, including subdomains). Archive Team wiki pages about 4chan may remain.

6. Copy **only** `assets/json/bookmarks_rota.json` into the website repo at `assets/json/bookmarks_rota.json` (default target: `frinjee.github.io`). Keep CI / cross-repo auto-push deferred until after a stable month of local Monday handoffs.

Rollback: restore `assets/json/bookmarks_rota.prev.json` over `bookmarks_rota.json` in this repo and/or the website repo.

Full weekly ops (review queue, taxonomy triage) live in [ig/task_plan.md](ig/task_plan.md). Site contract: [ig/implementation_update.md](ig/implementation_update.md).

## Tests

```powershell
pip install -e ".[dev]"
pytest tests/ -v
```

## Dead-link scan (Phase 2)

After a pipeline run, with the `health` extra installed:

```powershell
python -m bookmark_pipeline.link_health --db out/bookmarks.db --limit 50 --no-mark-inactive
```

## Site rota feed

Build or validate `bookmarks_rota.json` (requires `schema` extra for `--validate`):

```powershell
Copy-Item assets/json/bookmarks_rota.json assets/json/bookmarks_rota.prev.json -ErrorAction SilentlyContinue
python -m bookmark_pipeline.rota_feed build --rotation out/rotation_weekly.json --catalog out/bookmark_catalog.json --output assets/json/bookmarks_rota.json --validate
python -m bookmark_pipeline.rota_feed validate --feed assets/json/bookmarks_rota.json
```

See [ig/implementation_update.md](ig/implementation_update.md) for the site contract.
