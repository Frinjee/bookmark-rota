from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .audit import write_json
from .site_feed_blocklist import is_blocked_site_feed_url

SCHEMA_PATH = Path(__file__).resolve().parent.parent / 'schemas' / 'bookmarks_rota.schema.json'

def _catalog_index(catalog: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item['bookmark_id']): item for item in catalog}


def build_rota_feed(
    rotation: list[dict[str, Any]],
    catalog: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id = _catalog_index(catalog)
    feed: list[dict[str, Any]] = []
    for entry in rotation:
        bookmark_id = str(entry['bookmark_id'])
        record = by_id.get(bookmark_id)
        if record is None:
            continue
        if record.get('visibility_flag') != 'PUBLIC':
            continue
        url = str(record.get('url', ''))
        if not url.startswith(('http://', 'https://')):
            continue
        if is_blocked_site_feed_url(url):
            continue
        tags = record.get('tags', [])
        if not isinstance(tags, list):
            tags = []
        item = {
            'bookmark_id': bookmark_id,
            'title': str(entry.get('title', record.get('title', ''))),
            'url': url,
            'hash': str(entry['hash']),
            'display_week': str(entry['display_week']),
            'display_date': str(entry['display_date']),
            'taxonomy_category': str(record.get('taxonomy_category', '')),
            'taxonomy_subcategory': str(record.get('taxonomy_subcategory', '')),
            'tags': [str(tag) for tag in tags],
            'note': '',
        }
        feed.append(item)
    return feed


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def _require_jsonschema():
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            'rota feed validation requires jsonschema; install with: pip install -e ".[schema]"'
        ) from exc
    return jsonschema


def validate_rota_feed(feed: list[dict[str, Any]], *, schema_path: Path | None = None) -> None:
    jsonschema = _require_jsonschema()
    path = schema_path or SCHEMA_PATH
    schema = _load_json(path)
    jsonschema.validate(instance=feed, schema=schema)

    bookmark_ids = [item['bookmark_id'] for item in feed]
    hashes = [item['hash'] for item in feed]
    if len(bookmark_ids) != len(set(bookmark_ids)):
        raise ValueError('duplicate bookmark_id in rota feed')
    if len(hashes) != len(set(hashes)):
        raise ValueError('duplicate hash in rota feed')


def write_rota_feed(path: Path, feed: list[dict[str, Any]]) -> None:
    ordered: list[dict[str, Any]] = []
    for item in feed:
        ordered.append(
            {
                'bookmark_id': item['bookmark_id'],
                'title': item['title'],
                'url': item['url'],
                'hash': item['hash'],
                'display_week': item['display_week'],
                'display_date': item['display_date'],
                'taxonomy_category': item['taxonomy_category'],
                'taxonomy_subcategory': item['taxonomy_subcategory'],
                'tags': item['tags'],
                'note': item.get('note', ''),
            }
        )
    write_json(path, ordered)


def main() -> int:
    parser = argparse.ArgumentParser(description='Build or validate bookmarks_rota.json site feed.')
    sub = parser.add_subparsers(dest='command', required=True)

    build_parser = sub.add_parser('build', help='Merge rotation_weekly.json with bookmark_catalog.json')
    build_parser.add_argument('--rotation', type=Path, required=True)
    build_parser.add_argument('--catalog', type=Path, required=True)
    build_parser.add_argument('--output', type=Path, required=True)
    build_parser.add_argument(
        '--validate',
        action='store_true',
        help='Run jsonschema validation before writing output.',
    )

    validate_parser = sub.add_parser('validate', help='Validate an existing bookmarks_rota.json file')
    validate_parser.add_argument('--feed', type=Path, required=True)
    validate_parser.add_argument('--schema', type=Path, default=SCHEMA_PATH)

    args = parser.parse_args()

    if args.command == 'build':
        rotation = _load_json(args.rotation)
        catalog = _load_json(args.catalog)
        if not isinstance(rotation, list) or not isinstance(catalog, list):
            raise SystemExit('rotation and catalog inputs must be JSON arrays')
        feed = build_rota_feed(rotation, catalog)
        if args.validate:
            validate_rota_feed(feed)
        write_rota_feed(args.output, feed)
        print(f'wrote {len(feed)} items to {args.output}')
        return 0

    if args.command == 'validate':
        feed = _load_json(args.feed)
        if not isinstance(feed, list):
            raise SystemExit('feed must be a JSON array')
        validate_rota_feed(feed, schema_path=args.schema)
        print(f'valid: {args.feed} ({len(feed)} items)')
        return 0

    return 1


if __name__ == '__main__':
    raise SystemExit(main())
