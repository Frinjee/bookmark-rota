from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from .audit import write_json
from .catalog import bookmark_record_to_dict, build_catalog
from .dedupe import dedupe_firefox_against_chrome
from .docx_parser import parse_docx_bookmarks
from .export_html import export_netscape
from .rotation import (
    bookmark_hashes_legacy,
    iso_week_key,
    load_display_counts,
    select_weekly_rotation,
    today_date,
)
from .storage import (
    append_display_history,
    init_db,
    replace_review_queue,
    sync_taxonomy,
    upsert_bookmarks,
)


def _date_or_today(raw: str | None) -> date:
    if not raw:
        return today_date()
    return datetime.strptime(raw, '%Y-%m-%d').date()


def run_pipeline(
    *,
    chrome_docx: Path,
    firefox_docx: Path,
    output_dir: Path,
    run_date: date,
    dry_run: bool = False,
) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    chrome_bookmarks = parse_docx_bookmarks(chrome_docx, 'chrome')
    firefox_bookmarks = parse_docx_bookmarks(firefox_docx, 'firefox')

    dedupe = dedupe_firefox_against_chrome(chrome_bookmarks, firefox_bookmarks)
    catalog, mapping_log, review_queue = build_catalog(chrome_bookmarks, dedupe.kept_firefox)

    db_path = output_dir / 'bookmarks.db'
    conn = init_db(db_path)
    try:
        sync_taxonomy(conn)
        upsert_bookmarks(conn, catalog)
        replace_review_queue(conn, review_queue)

        week_key = iso_week_key(run_date)
        counts, weeks_by_bookmark = load_display_counts(conn)
        rotation = select_weekly_rotation(
            catalog,
            counts,
            weeks_by_bookmark,
            week_key=week_key,
            display_date=run_date.isoformat(),
            cycle_size=12,
        )
        if not dry_run:
            append_display_history(conn, rotation)
    finally:
        conn.close()

    write_json(
        output_dir / 'bookmark_catalog.json',
        [bookmark_record_to_dict(item) for item in catalog],
    )
    write_json(output_dir / 'duplicate_log.json', [asdict(item) for item in dedupe.duplicate_log])
    write_json(output_dir / 'taxonomy_mapping.json', [asdict(item) for item in mapping_log])
    write_json(output_dir / 'review_queue.json', [asdict(item) for item in review_queue])
    write_json(output_dir / 'rotation_weekly.json', [asdict(item) for item in rotation])
    write_json(output_dir / 'bookmark_hashes.json', bookmark_hashes_legacy(rotation))

    html_export, export_warnings = export_netscape(catalog)
    (output_dir / 'merged_bookmarks.html').write_text(html_export, encoding='utf-8', newline='\n')
    write_json(output_dir / 'export_warnings.json', export_warnings)

    return {
        'chrome_parsed': len(chrome_bookmarks),
        'firefox_parsed': len(firefox_bookmarks),
        'firefox_kept': len(dedupe.kept_firefox),
        'duplicates': len(dedupe.duplicate_log),
        'catalog_records': len(catalog),
        'weekly_rotation': len(rotation),
        'review_queue': len(review_queue),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build canonical bookmark catalog and exports.')
    parser.add_argument(
        '--chrome-docx',
        default='ig/bookmarks_5_30_26.docx',
        help='Path to Chrome bookmarks DOCX export.',
    )
    parser.add_argument(
        '--firefox-docx',
        default='ig/bookmarks-ff.docx',
        help='Path to Firefox bookmarks DOCX export.',
    )
    parser.add_argument(
        '--output-dir',
        default='ig/out',
        help='Output folder for generated artifacts.',
    )
    parser.add_argument(
        '--run-date',
        default='2026-08-10',
        help='Run date in YYYY-MM-DD format for weekly rotation keys.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        help=(
            'Generate rotation output files without writing display history to the DB. '
            'Bookmarks shown in this run remain eligible for future rotations.'
        ),
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    stats = run_pipeline(
        chrome_docx=Path(args.chrome_docx),
        firefox_docx=Path(args.firefox_docx),
        output_dir=Path(args.output_dir),
        run_date=_date_or_today(args.run_date),
        dry_run=args.dry_run,
    )
    for key in sorted(stats):
        print(f'{key}: {stats[key]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
