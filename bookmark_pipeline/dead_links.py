from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .models import utc_now_iso


@dataclass(slots=True)
class DeadLinkReport:
    bookmark_id: str
    url: str
    observed_at: str
    error_detail: str


def load_public_active_bookmarks(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    rows = conn.execute(
        '''
        SELECT bookmark_id, url
        FROM bookmarks
        WHERE visibility_flag = 'PUBLIC' AND status = 'ACTIVE'
        ORDER BY bookmark_id
        '''
    ).fetchall()
    return [(str(row[0]), str(row[1])) for row in rows]


def append_dead_link_reports(conn: sqlite3.Connection, reports: list[DeadLinkReport]) -> None:
    if not reports:
        return
    conn.executemany(
        '''
        INSERT INTO dead_link_reports(bookmark_id, url, observed_at, error_detail, resolved)
        VALUES (?, ?, ?, ?, 0)
        ''',
        [
            (item.bookmark_id, item.url, item.observed_at, item.error_detail)
            for item in reports
        ],
    )
    conn.commit()


def mark_bookmarks_inactive(conn: sqlite3.Connection, bookmark_ids: list[str]) -> None:
    if not bookmark_ids:
        return
    conn.executemany(
        'UPDATE bookmarks SET status = ? WHERE bookmark_id = ?',
        [('INACTIVE', bookmark_id) for bookmark_id in bookmark_ids],
    )
    conn.commit()


def dead_link_report_from_check(
    bookmark_id: str,
    url: str,
    *,
    ok: bool,
    error_detail: str,
) -> DeadLinkReport | None:
    if ok:
        return None
    return DeadLinkReport(
        bookmark_id=bookmark_id,
        url=url,
        observed_at=utc_now_iso(),
        error_detail=error_detail,
    )
