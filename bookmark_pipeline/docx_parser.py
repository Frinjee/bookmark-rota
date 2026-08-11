from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from .models import ParsedBookmark

NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'pr': 'http://schemas.openxmlformats.org/package/2006/relationships',
}

URL_PATTERN = re.compile(r'https?://[^\s<>\"]+')


def _extract_relationships(archive: zipfile.ZipFile) -> dict[str, str]:
    rels: dict[str, str] = {}
    try:
        rel_root = ET.fromstring(archive.read('word/_rels/document.xml.rels'))
    except KeyError:
        return rels

    for rel in rel_root.findall('.//pr:Relationship', NS):
        rel_id = rel.attrib.get('Id')
        target = rel.attrib.get('Target')
        rel_type = rel.attrib.get('Type', '')
        if rel_id and target and rel_type.endswith('/hyperlink'):
            rels[rel_id] = target
    return rels


def _heading_level(paragraph: ET.Element) -> int | None:
    pstyle = paragraph.find('./w:pPr/w:pStyle', NS)
    if pstyle is None:
        return None
    value = pstyle.attrib.get(f'{{{NS["w"]}}}val', '')
    if not value.startswith('Heading'):
        return None
    suffix = value.replace('Heading', '')
    if suffix.isdigit():
        return int(suffix)
    return None


def _paragraph_text(paragraph: ET.Element) -> str:
    return ''.join(
        node.text for node in paragraph.findall('.//w:t', NS) if node.text
    ).strip()


def parse_docx_bookmarks(path: Path, source_browser: str) -> list[ParsedBookmark]:
    with zipfile.ZipFile(path) as archive:
        document_root = ET.fromstring(archive.read('word/document.xml'))
        rels = _extract_relationships(archive)

    stack: dict[int, str] = {}
    parsed: list[ParsedBookmark] = []

    for paragraph in document_root.findall('.//w:p', NS):
        level = _heading_level(paragraph)
        text = _paragraph_text(paragraph)
        if level is not None and text:
            stack[level] = text
            for drop in list(stack):
                if drop > level:
                    del stack[drop]
            continue

        folder_parts = [stack[l] for l in sorted(stack) if stack[l]]
        folder_path = '/'.join(folder_parts)
        seen_urls: set[str] = set()

        for hyperlink in paragraph.findall('.//w:hyperlink', NS):
            rel_id = hyperlink.attrib.get(f'{{{NS["r"]}}}id')
            url = rels.get(rel_id or '', '').strip()
            title = ''.join(
                node.text for node in hyperlink.findall('.//w:t', NS) if node.text
            ).strip()
            if not url:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            parsed.append(
                ParsedBookmark(
                    title=title or url,
                    url=url,
                    folder_path=folder_path,
                    source_browser=source_browser,
                )
            )

        # broken exports can collapse links into plain text paragraphs
        for url in URL_PATTERN.findall(text):
            if url in seen_urls:
                continue
            seen_urls.add(url)
            parsed.append(
                ParsedBookmark(
                    title=url,
                    url=url,
                    folder_path=folder_path,
                    source_browser=source_browser,
                )
            )

    return parsed
