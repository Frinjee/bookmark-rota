from __future__ import annotations

import html
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlsplit

from .models import BookmarkRecord


def _epoch_from_iso(value: str) -> int:
    try:
        parsed = datetime.fromisoformat(value.replace('Z', ''))
        return int(parsed.timestamp())
    except ValueError:
        return int(datetime.utcnow().timestamp())


def _is_valid_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return bool(parts.scheme and parts.netloc)


def export_netscape(records: list[BookmarkRecord]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    tree: dict[tuple[str, str, str], list[BookmarkRecord]] = defaultdict(list)
    for rec in records:
        if not _is_valid_url(rec.url):
            warnings.append(f'invalid_url:{rec.bookmark_id}:{rec.url}')
            continue
        tree[(rec.taxonomy_category, rec.taxonomy_subcategory, rec.taxonomy_leaf)].append(rec)

    lines = [
        '<!DOCTYPE NETSCAPE-Bookmark-file-1>',
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        '<TITLE>Bookmarks</TITLE>',
        '<H1>Bookmarks</H1>',
        '<DL><p>',
    ]

    for key in sorted(tree):
        category, subcategory, leaf = key
        lines.append(f'  <DT><H3>{html.escape(category)}</H3>')
        lines.append('  <DL><p>')
        lines.append(f'    <DT><H3>{html.escape(subcategory or "GENERAL")}</H3>')
        lines.append('    <DL><p>')
        if leaf:
            lines.append(f'      <DT><H3>{html.escape(leaf)}</H3>')
            lines.append('      <DL><p>')
            indent = '        '
            closing = ['      </DL><p>']
        else:
            indent = '      '
            closing = []

        sorted_records = sorted(tree[key], key=lambda rec: (rec.title.lower(), rec.url))
        for rec in sorted_records:
            add_date = _epoch_from_iso(rec.date_added)
            lines.append(
                f'{indent}<DT><A HREF="{html.escape(rec.url)}" ADD_DATE="{add_date}">'
                f'{html.escape(rec.title)}</A>'
            )

        lines.extend(closing)
        lines.append('    </DL><p>')
        lines.append('  </DL><p>')

    lines.append('</DL><p>')
    lines.append('')
    return '\n'.join(lines), warnings
