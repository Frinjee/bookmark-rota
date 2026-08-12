from __future__ import annotations

import unittest

from bookmark_pipeline.url_normalizer import normalize_url


class UrlNormalizerTests(unittest.TestCase):
    def test_removes_tracking_parameters(self) -> None:
        url = (
            'https://Example.com:443/path/?utm_source=x&fbclid=abc&id=1&source=z'
        )
        normalized = normalize_url(url)
        self.assertEqual(normalized, 'https://example.com/path?id=1')

    def test_adds_default_scheme(self) -> None:
        self.assertEqual(normalize_url('example.com/test/'), 'https://example.com/test')


if __name__ == '__main__':
    unittest.main()
