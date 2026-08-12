from __future__ import annotations

import unittest

from bookmark_pipeline.classifier import classify_bookmark
from bookmark_pipeline.taxonomy import classify_from_path, validate_taxonomy_shape


class TaxonomyTests(unittest.TestCase):
    def test_taxonomy_limits_are_valid(self) -> None:
        validate_taxonomy_shape()

    def test_classify_from_path(self) -> None:
        mapped = classify_from_path('Bookmarks/INFSEC/OSINT')
        self.assertEqual(mapped, ('INFSEC', 'OSINT', ''))

    def test_keyword_classifier(self) -> None:
        result = classify_bookmark(
            title='IntelTechniques OSINT Tool',
            normalized_url='https://inteltechniques.com/tools',
            domain='inteltechniques.com',
            folder_path='Imported',
        )
        self.assertEqual(result.category, 'INFSEC')
        self.assertEqual(result.subcategory, 'OSINT')
        self.assertGreaterEqual(result.confidence, 80)


if __name__ == '__main__':
    unittest.main()
