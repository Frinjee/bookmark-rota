from __future__ import annotations

import unittest

from bookmark_pipeline.export_html import export_netscape
from bookmark_pipeline.models import BookmarkRecord


class ExportHtmlTests(unittest.TestCase):
    def test_malformed_url_is_logged(self) -> None:
        records = [
            BookmarkRecord(
                bookmark_id='1',
                title='Bad',
                url='not a url',
                normalized_url='not a url',
                domain='',
                taxonomy_category='UTILITIES',
                taxonomy_subcategory='GENERAL',
                taxonomy_leaf='',
                tags=[],
                tag_confidence={},
                visibility_flag='PUBLIC',
                status='ACTIVE',
                source_browser='chrome',
                source_path='Bookmarks',
                date_added='2026-08-10',
                last_seen='2026-08-10',
                classification_confidence=50,
            ),
            BookmarkRecord(
                bookmark_id='2',
                title='Good',
                url='https://example.com',
                normalized_url='https://example.com/',
                domain='example.com',
                taxonomy_category='UTILITIES',
                taxonomy_subcategory='GENERAL',
                taxonomy_leaf='',
                tags=[],
                tag_confidence={},
                visibility_flag='PUBLIC',
                status='ACTIVE',
                source_browser='chrome',
                source_path='Bookmarks',
                date_added='2026-08-10',
                last_seen='2026-08-10',
                classification_confidence=90,
            ),
        ]
        html, warnings = export_netscape(records)
        self.assertIn('<!DOCTYPE NETSCAPE-Bookmark-file-1>', html)
        self.assertTrue(any(item.startswith('invalid_url:1') for item in warnings))


if __name__ == '__main__':
    unittest.main()
