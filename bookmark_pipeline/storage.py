from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import BookmarkRecord, ReviewQueueEntry, RotationEntry
from .taxonomy import CANONICAL_TAXONOMY


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA foreign_keys = ON')

    conn.executescript(
        '''
        CREATE TABLE IF NOT EXISTS bookmarks (
            bookmark_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            normalized_url TEXT NOT NULL,
            domain TEXT NOT NULL,
            taxonomy_category TEXT NOT NULL,
            taxonomy_subcategory TEXT NOT NULL,
            taxonomy_leaf TEXT NOT NULL,
            visibility_flag TEXT NOT NULL,
            status TEXT NOT NULL,
            source_browser TEXT NOT NULL,
            source_path TEXT NOT NULL,
            date_added TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            classification_confidence INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bookmark_tags (
            bookmark_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            confidence INTEGER NOT NULL,
            PRIMARY KEY (bookmark_id, tag),
            FOREIGN KEY (bookmark_id) REFERENCES bookmarks(bookmark_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS bookmark_display_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bookmark_id TEXT NOT NULL,
            display_week TEXT NOT NULL,
            display_date TEXT NOT NULL,
            display_count INTEGER NOT NULL,
            FOREIGN KEY (bookmark_id) REFERENCES bookmarks(bookmark_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS bookmark_review_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bookmark_id TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            source_path TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS dead_link_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bookmark_id TEXT NOT NULL,
            url TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            error_detail TEXT NOT NULL,
            resolved INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS taxonomy_definitions (
            category TEXT NOT NULL,
            subcategory TEXT NOT NULL,
            leaf TEXT NOT NULL,
            PRIMARY KEY (category, subcategory, leaf)
        );
        '''
    )
    return conn


def sync_taxonomy(conn: sqlite3.Connection) -> None:
    rows: list[tuple[str, str, str]] = []
    for category, subcategories in CANONICAL_TAXONOMY.items():
        for subcategory, leaves in subcategories.items():
            if leaves:
                for leaf in leaves:
                    rows.append((category, subcategory, leaf))
            else:
                rows.append((category, subcategory, ''))
    conn.executemany(
        '''
        INSERT INTO taxonomy_definitions(category, subcategory, leaf)
        VALUES (?, ?, ?)
        ON CONFLICT(category, subcategory, leaf) DO NOTHING
        ''',
        rows,
    )
    conn.commit()


def upsert_bookmarks(conn: sqlite3.Connection, records: list[BookmarkRecord]) -> None:
    conn.executemany(
        '''
        INSERT INTO bookmarks(
            bookmark_id, title, url, normalized_url, domain,
            taxonomy_category, taxonomy_subcategory, taxonomy_leaf,
            visibility_flag, status, source_browser, source_path,
            date_added, last_seen, classification_confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(bookmark_id) DO UPDATE SET
            title=excluded.title,
            url=excluded.url,
            normalized_url=excluded.normalized_url,
            domain=excluded.domain,
            taxonomy_category=excluded.taxonomy_category,
            taxonomy_subcategory=excluded.taxonomy_subcategory,
            taxonomy_leaf=excluded.taxonomy_leaf,
            visibility_flag=excluded.visibility_flag,
            status=excluded.status,
            source_browser=excluded.source_browser,
            source_path=excluded.source_path,
            date_added=excluded.date_added,
            last_seen=excluded.last_seen,
            classification_confidence=excluded.classification_confidence
        ''',
        [
            (
                rec.bookmark_id,
                rec.title,
                rec.url,
                rec.normalized_url,
                rec.domain,
                rec.taxonomy_category,
                rec.taxonomy_subcategory,
                rec.taxonomy_leaf,
                rec.visibility_flag,
                rec.status,
                rec.source_browser,
                rec.source_path,
                rec.date_added,
                rec.last_seen,
                rec.classification_confidence,
            )
            for rec in records
        ],
    )
    conn.execute('DELETE FROM bookmark_tags')
    conn.executemany(
        '''
        INSERT INTO bookmark_tags(bookmark_id, tag, confidence)
        VALUES (?, ?, ?)
        ''',
        [
            (rec.bookmark_id, tag, confidence)
            for rec in records
            for tag, confidence in rec.tag_confidence.items()
        ],
    )
    conn.commit()


def replace_review_queue(conn: sqlite3.Connection, entries: list[ReviewQueueEntry]) -> None:
    conn.execute('DELETE FROM bookmark_review_queue')
    conn.executemany(
        '''
        INSERT INTO bookmark_review_queue(
            bookmark_id, title, url, reason, created_at, source_path
        ) VALUES (?, ?, ?, ?, ?, ?)
        ''',
        [
            (
                item.bookmark_id,
                item.title,
                item.url,
                item.reason,
                item.created_at,
                item.source_path,
            )
            for item in entries
        ],
    )
    conn.commit()


def append_display_history(conn: sqlite3.Connection, entries: list[RotationEntry]) -> None:
    conn.executemany(
        '''
        INSERT INTO bookmark_display_history(bookmark_id, display_week, display_date, display_count)
        VALUES (?, ?, ?, ?)
        ''',
        [
            (entry.bookmark_id, entry.display_week, entry.display_date, entry.display_count)
            for entry in entries
        ],
    )
    conn.commit()
