from __future__ import annotations

import unittest
from collections import Counter

from bookmark_pipeline.models import BookmarkRecord
from bookmark_pipeline.rotation import select_weekly_rotation


def _record(idx: int, category: str = 'DEV') -> BookmarkRecord:
    return BookmarkRecord(
        bookmark_id=f'id-{idx}',
        title=f'title-{idx}',
        url=f'https://example.com/{idx}',
        normalized_url=f'https://example.com/{idx}',
        domain='example.com',
        taxonomy_category=category,
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
        classification_confidence=95,
    )


class RotationTests(unittest.TestCase):
    def test_selects_exact_cycle_size(self) -> None:
        records = [_record(i, 'DEV' if i % 2 == 0 else 'INFSEC') for i in range(40)]
        picked = select_weekly_rotation(
            records,
            Counter(),
            {},
            week_key='2026-W33',
            display_date='2026-08-10',
            cycle_size=12,
            category_targets={'DEV': 6, 'INFSEC': 6},
        )
        self.assertEqual(len(picked), 12)
        self.assertEqual(len({entry.bookmark_id for entry in picked}), 12)


if __name__ == '__main__':
    unittest.main()
