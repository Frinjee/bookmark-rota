from __future__ import annotations

import time
import unittest

from bookmark_pipeline.classifier import classify_bookmark
from bookmark_pipeline.models import ParsedBookmark
from bookmark_pipeline.url_normalizer import domain_from_url, normalize_url


def _synthetic_bookmarks(count: int) -> list[ParsedBookmark]:
    items: list[ParsedBookmark] = []
    for idx in range(count):
        items.append(
            ParsedBookmark(
                title=f'OSINT Tool {idx}',
                url=f'https://example{idx % 50}.org/tool/{idx}?utm_source=test',
                folder_path='Bookmarks/INFSEC/OSINT',
                source_browser='chrome',
            )
        )
    return items


def run_scale_validation(size: int) -> float:
    start = time.perf_counter()
    data = _synthetic_bookmarks(size)
    for item in data:
        normalized = normalize_url(item.url)
        classify_bookmark(
            title=item.title,
            normalized_url=normalized,
            domain=domain_from_url(normalized),
            folder_path=item.folder_path,
        )
    return time.perf_counter() - start


class ScaleTests(unittest.TestCase):
    def test_scale_10k_under_reasonable_time(self) -> None:
        elapsed = run_scale_validation(10_000)
        self.assertLess(elapsed, 8.0)


if __name__ == '__main__':
    unittest.main()
