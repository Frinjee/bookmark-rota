from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bookmark_pipeline.dead_links import DeadLinkReport, append_dead_link_reports
from bookmark_pipeline.link_health import probe_url, scan_bookmark_urls
from bookmark_pipeline.storage import init_db


@pytest.fixture
def memory_db(tmp_path):
    db_path = tmp_path / 'bookmarks.db'
    conn = init_db(db_path)
    conn.execute(
        '''
        INSERT INTO bookmarks(
            bookmark_id, title, url, normalized_url, domain,
            taxonomy_category, taxonomy_subcategory, taxonomy_leaf,
            visibility_flag, status, source_browser, source_path,
            date_added, last_seen, classification_confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            'id1',
            'Example',
            'https://example.com',
            'https://example.com',
            'example.com',
            'DEV',
            'TOOLS',
            'MISC',
            'PUBLIC',
            'ACTIVE',
            'chrome',
            'Bookmarks',
            '2026-01-01',
            '2026-01-01',
            90,
        ),
    )
    conn.commit()
    yield conn
    conn.close()


def test_append_dead_link_reports(memory_db) -> None:
    reports = [
        DeadLinkReport(
            bookmark_id='id1',
            url='https://example.com',
            observed_at='2026-08-10T00:00:00Z',
            error_detail='HTTP 404',
        )
    ]
    append_dead_link_reports(memory_db, reports)
    row = memory_db.execute('SELECT bookmark_id, error_detail FROM dead_link_reports').fetchone()
    assert row == ('id1', 'HTTP 404')


httpx = pytest.importorskip('httpx')


def test_probe_url_success() -> None:
    client = MagicMock()
    response = MagicMock()
    response.status_code = 200
    client.head.return_value = response

    ok, status_code, detail = probe_url(client, 'https://example.com')
    assert ok is True
    assert status_code == 200
    assert detail == ''


def test_scan_bookmark_urls_uses_client() -> None:
    with patch('bookmark_pipeline.link_health.httpx.Client') as client_cls:
        client = MagicMock()
        client_cls.return_value.__enter__.return_value = client
        response = MagicMock()
        response.status_code = 200
        client.head.return_value = response

        results = scan_bookmark_urls([('b1', 'https://example.com')])
        assert len(results) == 1
        assert results[0].ok is True
