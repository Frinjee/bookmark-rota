from __future__ import annotations

import unittest
from collections import Counter

from bookmark_pipeline.models import BookmarkRecord
from bookmark_pipeline.rotation import backfill_weekly_rotation, select_weekly_rotation


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

    def test_excludes_4chan_hosts_and_search_indexers(self) -> None:
        records = [_record(i) for i in range(20)]
        records.append(
            BookmarkRecord(
                bookmark_id='boards',
                title='boards',
                url='https://boards.4chan.org/g/',
                normalized_url='https://boards.4chan.org/g',
                domain='boards.4chan.org',
                taxonomy_category='DEV',
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
        )
        records.append(
            BookmarkRecord(
                bookmark_id='find4',
                title='find',
                url='https://find.4chan.org/?q=test',
                normalized_url='https://find.4chan.org/?q=test',
                domain='find.4chan.org',
                taxonomy_category='DEV',
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
        )
        records.append(
            BookmarkRecord(
                bookmark_id='search4',
                title='search',
                url='https://4chansearch.com/',
                normalized_url='https://4chansearch.com/',
                domain='4chansearch.com',
                taxonomy_category='DEV',
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
        )
        wiki = BookmarkRecord(
            bookmark_id='wiki4',
            title='4chan - Archiveteam',
            url='https://wiki.archiveteam.org/index.php/4chan',
            normalized_url='https://wiki.archiveteam.org/index.php/4chan',
            domain='wiki.archiveteam.org',
            taxonomy_category='DEV',
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
        records.append(wiki)
        picked = select_weekly_rotation(
            records,
            Counter(),
            {},
            week_key='2026-W33',
            display_date='2026-08-10',
            cycle_size=12,
        )
        ids = {entry.bookmark_id for entry in picked}
        self.assertEqual(len(picked), 12)
        self.assertNotIn('boards', ids)
        self.assertNotIn('find4', ids)
        self.assertNotIn('search4', ids)
        self.assertIn('wiki4', ids)

    def test_backfill_keeps_existing_ids_and_skips_blocked(self) -> None:
        records = [_record(i) for i in range(20)]
        records.append(
            BookmarkRecord(
                bookmark_id='search4',
                title='search',
                url='https://4chansearch.com/',
                normalized_url='https://4chansearch.com/',
                domain='4chansearch.com',
                taxonomy_category='DEV',
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
        )
        kept = [f'id-{i}' for i in range(10)]
        picked = backfill_weekly_rotation(
            kept + ['search4'],
            records,
            Counter(),
            {},
            week_key='2026-W33',
            display_date='2026-08-10',
            cycle_size=12,
        )
        ids = [entry.bookmark_id for entry in picked]
        self.assertEqual(ids[:10], kept)
        self.assertEqual(len(ids), 12)
        self.assertNotIn('search4', ids)
        self.assertEqual(len(set(ids)), 12)


if __name__ == '__main__':
    unittest.main()
