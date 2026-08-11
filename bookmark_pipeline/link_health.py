from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

try:
    from tenacity import retry, stop_after_attempt, wait_fixed
except ImportError:  # pragma: no cover
    retry = None  # type: ignore[assignment,misc]

from .dead_links import (
    DeadLinkReport,
    append_dead_link_reports,
    dead_link_report_from_check,
    load_public_active_bookmarks,
    mark_bookmarks_inactive,
)
from .storage import init_db


@dataclass(slots=True)
class LinkProbeResult:
    bookmark_id: str
    url: str
    ok: bool
    status_code: int | None
    error_detail: str


def _require_health_deps() -> None:
    if httpx is None:
        raise RuntimeError(
            'link health scan requires httpx; install with: pip install -e ".[health]"'
        )


def _probe_once(client: httpx.Client, url: str) -> tuple[bool, int | None, str]:
    try:
        response = client.head(url, follow_redirects=True)
        if response.status_code in (405, 501) or response.status_code >= 400:
            response = client.get(url, follow_redirects=True)
        status_code = response.status_code
        if status_code >= 400:
            return False, status_code, f'HTTP {status_code}'
        return True, status_code, ''
    except httpx.HTTPError as exc:
        return False, None, str(exc)


def probe_url(client: httpx.Client, url: str) -> tuple[bool, int | None, str]:
    if retry is not None:

        @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.5), reraise=True)
        def _with_retry() -> tuple[bool, int | None, str]:
            return _probe_once(client, url)

        try:
            return _with_retry()
        except httpx.HTTPError as exc:
            return False, None, str(exc)

    return _probe_once(client, url)


def scan_bookmark_urls(
    targets: list[tuple[str, str]],
    *,
    timeout_seconds: float = 15.0,
    user_agent: str = 'bookmark-rota-link-health/0.1',
) -> list[LinkProbeResult]:
    _require_health_deps()
    results: list[LinkProbeResult] = []
    headers = {'User-Agent': user_agent}
    with httpx.Client(timeout=timeout_seconds, headers=headers) as client:
        for bookmark_id, url in targets:
            ok, status_code, error_detail = probe_url(client, url)
            results.append(
                LinkProbeResult(
                    bookmark_id=bookmark_id,
                    url=url,
                    ok=ok,
                    status_code=status_code,
                    error_detail=error_detail,
                )
            )
    return results


def run_dead_link_scan(
    db_path: Path,
    *,
    mark_inactive: bool = True,
    limit: int | None = None,
) -> dict[str, int]:
    _require_health_deps()
    conn = init_db(db_path)
    try:
        targets = load_public_active_bookmarks(conn)
        if limit is not None:
            targets = targets[:limit]

        probe_results = scan_bookmark_urls(targets)
        reports: list[DeadLinkReport] = []
        failed_ids: list[str] = []
        for item in probe_results:
            report = dead_link_report_from_check(
                item.bookmark_id,
                item.url,
                ok=item.ok,
                error_detail=item.error_detail,
            )
            if report is not None:
                reports.append(report)
                failed_ids.append(item.bookmark_id)

        append_dead_link_reports(conn, reports)
        if mark_inactive and failed_ids:
            mark_bookmarks_inactive(conn, failed_ids)

        return {
            'checked': len(probe_results),
            'dead': len(reports),
            'marked_inactive': len(failed_ids) if mark_inactive else 0,
        }
    finally:
        conn.close()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description='Scan PUBLIC ACTIVE bookmarks for dead links.')
    parser.add_argument(
        '--db',
        default='out/bookmarks.db',
        help='Path to SQLite database from pipeline run.',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Optional cap on URLs checked (for testing).',
    )
    parser.add_argument(
        '--no-mark-inactive',
        action='store_true',
        help='Record dead links without setting bookmark status to INACTIVE.',
    )
    args = parser.parse_args()

    stats = run_dead_link_scan(
        Path(args.db),
        mark_inactive=not args.no_mark_inactive,
        limit=args.limit,
    )
    for key in sorted(stats):
        print(f'{key}: {stats[key]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
