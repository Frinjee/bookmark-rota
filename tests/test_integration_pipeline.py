from __future__ import annotations

import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import json
import sqlite3

from bookmark_pipeline.cli import run_pipeline


DOC_XML_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Bookmarks</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr><w:r><w:t>{folder}</w:t></w:r></w:p>
    <w:p>
      <w:hyperlink r:id="rId1"><w:r><w:t>{title1}</w:t></w:r></w:hyperlink>
      <w:hyperlink r:id="rId2"><w:r><w:t>{title2}</w:t></w:r></w:hyperlink>
    </w:p>
  </w:body>
</w:document>
'''

RELS_XML_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="{url1}" TargetMode="External"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="{url2}" TargetMode="External"/>
</Relationships>
'''

CONTENT_TYPES_XML = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
</Types>
'''


def _write_docx(path: Path, *, folder: str, title1: str, url1: str, title2: str, url2: str) -> None:
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            'word/document.xml',
            DOC_XML_TEMPLATE.format(folder=folder, title1=title1, title2=title2),
        )
        archive.writestr(
            'word/_rels/document.xml.rels',
            RELS_XML_TEMPLATE.format(url1=url1, url2=url2),
        )
        archive.writestr('[Content_Types].xml', CONTENT_TYPES_XML)


class IntegrationPipelineTests(unittest.TestCase):
    def test_pipeline_generates_expected_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            chrome = tmp_path / 'chrome.docx'
            firefox = tmp_path / 'firefox.docx'
            out_dir = tmp_path / 'out'

            _write_docx(
                chrome,
                folder='INFSEC',
                title1='OSINT Tool',
                url1='https://example.com/osint',
                title2='Python Docs',
                url2='https://python.org/docs',
            )
            _write_docx(
                firefox,
                folder='Imported',
                title1='OSINT Tool Duplicate',
                url1='https://example.com/osint?utm_source=x',
                title2='Unique Page',
                url2='https://unique.example.net',
            )

            stats = run_pipeline(
                chrome_docx=chrome,
                firefox_docx=firefox,
                output_dir=out_dir,
                run_date=date(2026, 8, 10),
            )

            self.assertGreater(stats['weekly_rotation'], 0)
            self.assertLessEqual(stats['weekly_rotation'], 12)
            self.assertTrue((out_dir / 'bookmark_catalog.json').exists())
            self.assertTrue((out_dir / 'duplicate_log.json').exists())
            self.assertTrue((out_dir / 'taxonomy_mapping.json').exists())
            self.assertTrue((out_dir / 'merged_bookmarks.html').exists())
            self.assertTrue((out_dir / 'bookmarks.db').exists())

    def test_private_records_are_obfuscated_in_exports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            chrome = tmp_path / 'chrome.docx'
            firefox = tmp_path / 'firefox.docx'
            out_dir = tmp_path / 'out'

            _write_docx(
                chrome,
                folder='job search',
                title1='My Private Application',
                url1='https://umb.taleo.net/careersection/jobdetail.ftl',
                title2='Public Python Docs',
                url2='https://python.org/docs',
            )
            _write_docx(
                firefox,
                folder='Imported',
                title1='Another Public Link',
                url1='https://example.com/public',
                title2='Reference',
                url2='https://example.org/ref',
            )

            with patch.dict('os.environ', {'BOOKMARK_ROTA_OBFUSCATION_KEY': 'test-secret'}, clear=False):
                run_pipeline(
                    chrome_docx=chrome,
                    firefox_docx=firefox,
                    output_dir=out_dir,
                    run_date=date(2026, 8, 10),
                    dry_run=True,
                )

            catalog = json.loads((out_dir / 'bookmark_catalog.json').read_text(encoding='utf-8'))
            private_record = next(item for item in catalog if item['visibility_flag'] == 'PRIVATE')
            public_record = next(item for item in catalog if item['visibility_flag'] == 'PUBLIC')

            self.assertTrue(private_record['title'].startswith('PRIVATE_'))
            self.assertTrue(private_record['url'].startswith('https://private.invalid/'))
            self.assertTrue(private_record['normalized_url'].startswith('https://private.invalid/'))
            self.assertEqual(private_record['domain'], 'private.invalid')
            self.assertTrue(private_record['source_path'].startswith('private/'))

            self.assertEqual(public_record['title'], 'Another Public Link')
            self.assertEqual(public_record['url'], 'https://example.com/public')

            html_export = (out_dir / 'merged_bookmarks.html').read_text(encoding='utf-8')
            self.assertNotIn('My Private Application', html_export)
            self.assertNotIn('umb.taleo.net', html_export)
            self.assertIn('PRIVATE_', html_export)

    def test_dry_run_does_not_write_history_and_obfuscation_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            chrome = tmp_path / 'chrome.docx'
            firefox = tmp_path / 'firefox.docx'
            out_dir = tmp_path / 'out'

            _write_docx(
                chrome,
                folder='job search',
                title1='My Private Application',
                url1='https://umb.taleo.net/careersection/jobdetail.ftl',
                title2='Public Python Docs',
                url2='https://python.org/docs',
            )
            _write_docx(
                firefox,
                folder='Imported',
                title1='Another Public Link',
                url1='https://example.com/public',
                title2='Reference',
                url2='https://example.org/ref',
            )

            with patch.dict('os.environ', {'BOOKMARK_ROTA_OBFUSCATION_KEY': 'test-secret'}, clear=False):
                run_pipeline(
                    chrome_docx=chrome,
                    firefox_docx=firefox,
                    output_dir=out_dir,
                    run_date=date(2026, 8, 10),
                    dry_run=True,
                )
                catalog_first = (out_dir / 'bookmark_catalog.json').read_text(encoding='utf-8')
                rotation_first = (out_dir / 'rotation_weekly.json').read_text(encoding='utf-8')
                run_pipeline(
                    chrome_docx=chrome,
                    firefox_docx=firefox,
                    output_dir=out_dir,
                    run_date=date(2026, 8, 10),
                    dry_run=True,
                )
                catalog_second = (out_dir / 'bookmark_catalog.json').read_text(encoding='utf-8')
                rotation_second = (out_dir / 'rotation_weekly.json').read_text(encoding='utf-8')

            self.assertEqual(catalog_first, catalog_second)
            self.assertEqual(rotation_first, rotation_second)

            conn = sqlite3.connect(out_dir / 'bookmarks.db')
            try:
                history_count = conn.execute('SELECT COUNT(*) FROM bookmark_display_history').fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(history_count, 0)

    def test_private_records_require_obfuscation_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            chrome = tmp_path / 'chrome.docx'
            firefox = tmp_path / 'firefox.docx'
            out_dir = tmp_path / 'out'

            _write_docx(
                chrome,
                folder='job search',
                title1='Private item',
                url1='https://umb.taleo.net/careersection/jobdetail.ftl',
                title2='Public item',
                url2='https://example.com/public',
            )
            _write_docx(
                firefox,
                folder='Imported',
                title1='Public 2',
                url1='https://example.org/2',
                title2='Public 3',
                url2='https://example.net/3',
            )

            with patch.dict('os.environ', {}, clear=True):
                with self.assertRaisesRegex(ValueError, 'BOOKMARK_ROTA_OBFUSCATION_KEY'):
                    run_pipeline(
                        chrome_docx=chrome,
                        firefox_docx=firefox,
                        output_dir=out_dir,
                        run_date=date(2026, 8, 10),
                        dry_run=True,
                    )


if __name__ == '__main__':
    unittest.main()
