from __future__ import annotations

import pytest

jsonschema = pytest.importorskip('jsonschema')

from bookmark_pipeline.rota_feed import build_rota_feed, validate_rota_feed


def test_build_rota_feed_enriches_from_catalog() -> None:
    rotation = [
        {
            'bookmark_id': 'abc',
            'title': 'Rotated title',
            'hash': 'deadbeef',
            'display_week': '2026-W33',
            'display_date': '2026-08-10',
            'display_count': 1,
        }
    ]
    catalog = [
        {
            'bookmark_id': 'abc',
            'title': 'Catalog title',
            'url': 'https://example.com/page',
            'visibility_flag': 'PUBLIC',
            'taxonomy_category': 'DEV',
            'taxonomy_subcategory': 'DOCS',
            'tags': ['DEV', 'DOCS'],
        }
    ]
    feed = build_rota_feed(rotation, catalog)
    assert len(feed) == 1
    assert feed[0]['url'] == 'https://example.com/page'
    assert feed[0]['taxonomy_category'] == 'DEV'
    assert feed[0]['hash'] == 'deadbeef'


def test_build_rota_feed_skips_non_public() -> None:
    rotation = [{'bookmark_id': 'x', 'title': 'T', 'hash': 'h', 'display_week': '2026-W33', 'display_date': '2026-08-10'}]
    catalog = [
        {
            'bookmark_id': 'x',
            'title': 'T',
            'url': 'https://example.com',
            'visibility_flag': 'PRIVATE',
            'taxonomy_category': 'DEV',
            'taxonomy_subcategory': 'X',
            'tags': [],
        }
    ]
    assert build_rota_feed(rotation, catalog) == []


def test_build_rota_feed_skips_blocked_4chan_hosts() -> None:
    rotation = [
        {'bookmark_id': 'a', 'title': 'Boards', 'hash': 'h1', 'display_week': '2026-W33', 'display_date': '2026-08-10'},
        {'bookmark_id': 'b', 'title': 'Find', 'hash': 'h2', 'display_week': '2026-W33', 'display_date': '2026-08-10'},
        {'bookmark_id': 'c', 'title': 'Search', 'hash': 'h3', 'display_week': '2026-W33', 'display_date': '2026-08-10'},
        {'bookmark_id': 'd', 'title': 'Wiki', 'hash': 'h4', 'display_week': '2026-W33', 'display_date': '2026-08-10'},
    ]
    catalog = [
        {
            'bookmark_id': 'a',
            'title': 'Boards',
            'url': 'https://boards.4chan.org/g/',
            'visibility_flag': 'PUBLIC',
            'taxonomy_category': 'DEV',
            'taxonomy_subcategory': 'X',
            'tags': [],
        },
        {
            'bookmark_id': 'b',
            'title': 'Find',
            'url': 'https://find.4chan.org/?q=test',
            'visibility_flag': 'PUBLIC',
            'taxonomy_category': 'DEV',
            'taxonomy_subcategory': 'X',
            'tags': [],
        },
        {
            'bookmark_id': 'c',
            'title': 'Search',
            'url': 'https://4chansearch.com/',
            'visibility_flag': 'PUBLIC',
            'taxonomy_category': 'DEV',
            'taxonomy_subcategory': 'X',
            'tags': [],
        },
        {
            'bookmark_id': 'd',
            'title': 'Wiki',
            'url': 'https://wiki.archiveteam.org/index.php/4chan',
            'visibility_flag': 'PUBLIC',
            'taxonomy_category': 'DEV',
            'taxonomy_subcategory': 'X',
            'tags': [],
        },
    ]
    feed = build_rota_feed(rotation, catalog)
    assert len(feed) == 1
    assert feed[0]['bookmark_id'] == 'd'
    assert 'archiveteam.org' in feed[0]['url']


def test_validate_rota_feed_sample_fixture() -> None:
    from pathlib import Path

    sample = Path(__file__).resolve().parent.parent / 'schemas' / 'fixtures' / 'bookmarks_rota.sample.json'
    import json

    feed = json.loads(sample.read_text(encoding='utf-8'))
    validate_rota_feed(feed)


def test_validate_rota_feed_rejects_duplicate_ids() -> None:
    feed = [
        {
            'bookmark_id': 'same',
            'title': 'A',
            'url': 'https://a.example',
            'hash': 'h1',
            'display_week': '2026-W33',
            'display_date': '2026-08-10',
            'taxonomy_category': 'DEV',
            'taxonomy_subcategory': 'X',
            'tags': [],
            'note': '',
        },
        {
            'bookmark_id': 'same',
            'title': 'B',
            'url': 'https://b.example',
            'hash': 'h2',
            'display_week': '2026-W33',
            'display_date': '2026-08-10',
            'taxonomy_category': 'DEV',
            'taxonomy_subcategory': 'X',
            'tags': [],
            'note': '',
        },
    ]
    with pytest.raises(ValueError, match='duplicate bookmark_id'):
        validate_rota_feed(feed)
