# bookmark-rota

Local pipeline that ingests Chrome and Firefox bookmark DOCX exports, deduplicates and classifies them, persists a catalog in SQLite, and emits JSON/HTML rotation artifacts.

## Python environment

Requires **Python 3.11+**.

Install the package and default runtime dependencies (includes **rapidfuzz** for fuzzy dedupe):

```powershell
cd c:\Users\jee\Documents\gh-repos\bookmark-rota
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

## Run pipeline

```powershell
python -m bookmark_pipeline `
  --chrome-docx ig/bookmarks_5_30_26.docx `
  --firefox-docx ig/bookmarks-ff.docx `
  --output-dir out `
  --run-date 2026-08-10
```

## Tests

```powershell
pip install -e ".[dev]"
pytest tests/ -v
```

## Dead-link scan (Phase 2)

After a pipeline run, with the `health` extra installed:

```powershell
python -m bookmark_pipeline.link_health --db out/bookmarks.db
```

## Site rota feed

Build or validate `bookmarks_rota.json` (requires `schema` extra for `--validate`):

```powershell
python -m bookmark_pipeline.rota_feed build --rotation out/rotation_weekly.json --catalog out/bookmark_catalog.json --output assets/json/bookmarks_rota.json
python -m bookmark_pipeline.rota_feed validate --feed assets/json/bookmarks_rota.json
```

See [ig/implementation_update.md](ig/implementation_update.md) for the site contract.
