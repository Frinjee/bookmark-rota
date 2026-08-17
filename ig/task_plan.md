# Weekly bookmark rota task plan

Start date: 2026-08-10  
Cadence: weekly, every Monday  
Selection size: 12 bookmarks per cycle

## objective

Run a deterministic weekly process that keeps the canonical catalog healthy, produces an audited 12-link rotation, and keeps generated artifacts ready for automation.

## weekly runbook

### 1) ingestion and sync

1. Confirm latest browser exports are present:
   - `ig/bookmarks_5_30_26.docx` (or latest Chrome export)
   - `ig/bookmarks-ff.docx` (or latest Firefox export)
   - export obfuscation key is set when PRIVATE records are expected:
     - `BOOKMARK_ROTA_OBFUSCATION_KEY=<local secret>`
2. Run pipeline:
   - `python -m bookmark_pipeline --chrome-docx ig/bookmarks_5_30_26.docx --firefox-docx ig/bookmarks-ff.docx --output-dir out --run-date YYYY-MM-DD`
3. Verify files were regenerated:
   - `out/bookmark_catalog.json`
   - `out/duplicate_log.json`
   - `out/taxonomy_mapping.json`
   - `out/review_queue.json`
   - `out/rotation_weekly.json`
   - `out/bookmark_hashes.json`
   - `out/merged_bookmarks.html`
   - `out/bookmarks.db`

### 2) dedupe and classification review

1. Review `duplicate_log.json` for false positives where confidence is below 90.
2. Review taxonomy assignments in `taxonomy_mapping.json`:
   - prioritize entries with confidence < 80
   - confirm high-risk paths (security/privacy topics) are classified correctly
3. If classification issues are found:
   - update rule patterns in `bookmark_pipeline/classifier.py`
   - rerun pipeline and confirm deterministic output deltas

### 3) review queue triage

1. Open `out/review_queue.json`.
2. Process by reason:
   - `taxonomy_unmatched`: map into canonical taxonomy or leave pending
   - `review_visibility`: confirm `PUBLIC` vs `REVIEW` vs `PRIVATE`
3. Re-run after rule or visibility adjustments.

### 4) weekly rotation generation and validation

1. Confirm `rotation_weekly.json` contains exactly 12 entries.
2. Confirm no duplicate `bookmark_id` values within the cycle.
3. Confirm each selected record is `PUBLIC` and `ACTIVE`.
4. Confirm no 4chan hosts or known 4chan search/indexers (`4chan.org`, `4channel.org`, `4cdn.org`, `4chansearch.com`, any subdomain) appear in the site feed. Keep Archive Team wiki pages about 4chan.
5. Spot-check recency:
   - ensure no item was shown in the last 4 ISO weeks when enough pool exists
6. Confirm `bookmark_hashes.json` has title/hash/week/display metadata.

### 5) dead-link and health checks

1. Weekly limited scan (review-first):
   - `python -m bookmark_pipeline.link_health --db out/bookmarks.db --limit 50 --no-mark-inactive`
2. For dead links found during the week:
   - leave inactive marking for scheduled cleanup after manual review
   - or route to review queue in the next pass
3. Keep dead-link decisions deterministic and reproducible.

### 6) site feed publish (Monday handoff)

Only one file leaves this repo for the website: `assets/json/bookmarks_rota.json`.

1. Back up the current feed before overwrite:
   - `Copy-Item assets/json/bookmarks_rota.json assets/json/bookmarks_rota.prev.json -ErrorAction SilentlyContinue`
2. Build and validate:
   - `python -m bookmark_pipeline.rota_feed build --rotation out/rotation_weekly.json --catalog out/bookmark_catalog.json --output assets/json/bookmarks_rota.json --validate`
3. Confirm gates:
   - exactly 12 items for a normal week (document intentional short weeks)
   - unique `bookmark_id` and `hash` values
   - every URL is absolute `http://` or `https://`
   - no 4chan hosts or known 4chan search/indexers (`4chan.org` / `4channel.org` / `4cdn.org` / `4chansearch.com` and subdomains)
4. Copy **only** `assets/json/bookmarks_rota.json` into the website repo path `assets/json/bookmarks_rota.json` (default: `frinjee.github.io`).
5. Rollback if needed: restore from `assets/json/bookmarks_rota.prev.json`.
6. Keep CI / cross-repo auto-push deferred until after ~4 local Monday handoffs.

### 7) automation-safe release checklist

1. Ensure generated JSON is sorted and stable across reruns with same inputs/date.
2. Run tests:
   - `pytest tests/ -v`
3. Optional scale sanity:
   - `python -c "from tests.test_scale import run_scale_validation; [print(s, run_scale_validation(s)) for s in (10000,50000,100000)]"`
4. Commit with a predictable message format:
   - `bookmark-rota: weekly run YYYY-MM-DD`
5. Publish the site feed per section 6 (not the full `out/` tree).

## monthly maintenance

1. Audit classifier precision and adjust keyword rules.
2. Review category balance in weekly output and tune `category_targets`.
3. Vacuum/analyze `out/bookmarks.db` if growth increases.
4. Review `PRIVATE` and `REVIEW` backlog for stale entries.

## escalation points

- If duplicate confidence logic causes unwanted removals, lower fuzzy influence and require stronger normalized/path agreement.
- If review queue grows for two consecutive weeks, add focused taxonomy rules instead of manual one-off edits.
- If runtime exceeds acceptable limits at 100k+, move heavy joins/scoring to sqlite-backed staging.

## phase 2 planning handoff packet

Prepare this packet immediately after a successful Phase 1 build/test run:

1. Baseline metrics snapshot:
   - counts from `out/bookmark_catalog.json`, `out/review_queue.json`, `out/rotation_weekly.json`
   - visibility split and `UNSORTED` concentration
2. Contract snapshot:
   - `rotation_weekly.json` fields consumed by `rota_feed`
   - `bookmark_catalog.json` enrichment fields consumed by `rota_feed`
3. Health-scan readiness:
   - `bookmark_pipeline.link_health` dependencies installed and dry-run command validated
4. Locked decisions for Phase 2 kickoff:
   - gate targets: `UNSORTED <= 910`, `review_queue <= 930`, `rotation distinct categories >= 4`, `UNSORTED in rotation <= 8/12`
   - dead-link remediation: review-first weekly (`--no-mark-inactive`), immediate inactive only in scheduled cleanup runs
   - category-diversity quotas: implement in first Phase 2 delivery slice
