from __future__ import annotations

import unittest

from bookmark_pipeline.site_feed_blocklist import (
    is_blocked_site_feed_host,
    is_blocked_site_feed_url,
)


class SiteFeedBlocklistTests(unittest.TestCase):
    def test_blocks_official_hosts_and_subdomains(self) -> None:
        self.assertTrue(is_blocked_site_feed_host('4chan.org'))
        self.assertTrue(is_blocked_site_feed_host('boards.4chan.org'))
        self.assertTrue(is_blocked_site_feed_host('find.4chan.org'))
        self.assertTrue(is_blocked_site_feed_host('4channel.org'))
        self.assertTrue(is_blocked_site_feed_host('i.4cdn.org'))

    def test_blocks_known_search_indexers(self) -> None:
        self.assertTrue(is_blocked_site_feed_host('4chansearch.com'))
        self.assertTrue(is_blocked_site_feed_host('www.4chansearch.com'))
        self.assertTrue(is_blocked_site_feed_url('https://4chansearch.com/'))
        self.assertTrue(is_blocked_site_feed_url('https://find.4chan.org/?q=test'))

    def test_keeps_archive_team_wiki_and_unrelated_hosts(self) -> None:
        self.assertFalse(is_blocked_site_feed_url(
            'https://wiki.archiveteam.org/index.php/4chan#The_Second_4archive.org'
        ))
        self.assertFalse(is_blocked_site_feed_host('not4chan.org'))
        self.assertFalse(is_blocked_site_feed_host('example.com'))
        self.assertFalse(is_blocked_site_feed_url('https://example.com/4chan'))


if __name__ == '__main__':
    unittest.main()
