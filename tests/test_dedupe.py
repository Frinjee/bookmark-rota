from __future__ import annotations

import unittest

from bookmark_pipeline.dedupe import dedupe_firefox_against_chrome
from bookmark_pipeline.models import ParsedBookmark


class DedupeTests(unittest.TestCase):
    def test_exact_and_normalized_duplicates_removed(self) -> None:
        chrome = [
            ParsedBookmark(
                title='A',
                url='https://example.com/path',
                folder_path='Bookmarks/DEV',
                source_browser='chrome',
            )
        ]
        firefox = [
            ParsedBookmark(
                title='A duplicate exact',
                url='https://example.com/path',
                folder_path='Firefox/Stuff',
                source_browser='firefox',
            ),
            ParsedBookmark(
                title='A duplicate normalized',
                url='https://EXAMPLE.com/path/?utm_source=abc',
                folder_path='Firefox/Stuff',
                source_browser='firefox',
            ),
            ParsedBookmark(
                title='Unique',
                url='https://another.example.org',
                folder_path='Firefox/Stuff',
                source_browser='firefox',
            ),
        ]

        result = dedupe_firefox_against_chrome(chrome, firefox)
        self.assertEqual(len(result.duplicate_log), 2)
        self.assertEqual(len(result.kept_firefox), 1)
        self.assertEqual(result.kept_firefox[0].title, 'Unique')


if __name__ == '__main__':
    unittest.main()
