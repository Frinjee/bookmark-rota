from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import replace

from .models import BookmarkRecord


OBFUSCATION_KEY_ENV = 'BOOKMARK_ROTA_OBFUSCATION_KEY'
PRIVATE_VISIBILITY = 'PRIVATE'


def obfuscation_key_from_env() -> str:
    return os.getenv(OBFUSCATION_KEY_ENV, '').strip()


def require_obfuscation_key(records: list[BookmarkRecord], key: str) -> None:
    if key:
        return
    if any(rec.visibility_flag == PRIVATE_VISIBILITY for rec in records):
        raise ValueError(
            f'{OBFUSCATION_KEY_ENV} is required when PRIVATE bookmarks are present in exports.'
        )


def _token(key: str, namespace: str, value: str) -> str:
    payload = f'{namespace}:{value}'.encode('utf-8')
    digest = hmac.new(key.encode('utf-8'), payload, hashlib.sha256).hexdigest()
    return digest


def _private_url(key: str, namespace: str, value: str) -> str:
    return f'https://private.invalid/{_token(key, namespace, value)[:24]}'


def obfuscate_private_records(records: list[BookmarkRecord], key: str) -> list[BookmarkRecord]:
    if not key:
        return records

    obfuscated: list[BookmarkRecord] = []
    for rec in records:
        if rec.visibility_flag != PRIVATE_VISIBILITY:
            obfuscated.append(rec)
            continue

        title_token = _token(key, 'title', rec.title)
        path_token = _token(key, 'source_path', rec.source_path)
        obfuscated.append(
            replace(
                rec,
                title=f'PRIVATE_{title_token[:12]}',
                url=_private_url(key, 'url', rec.url),
                normalized_url=_private_url(key, 'normalized_url', rec.normalized_url),
                domain='private.invalid',
                source_path=f'private/{path_token[:16]}',
                metadata={'obfuscated': True},
            )
        )
    return obfuscated


def obfuscate_private_rotation_payload(
    rotation_payload: list[dict[str, object]],
    private_ids: set[str],
    key: str,
) -> list[dict[str, object]]:
    if not key or not private_ids:
        return rotation_payload

    obfuscated: list[dict[str, object]] = []
    for entry in rotation_payload:
        bookmark_id = str(entry.get('bookmark_id', ''))
        if bookmark_id not in private_ids:
            obfuscated.append(entry)
            continue

        updated = dict(entry)
        updated['title'] = f"PRIVATE_{_token(key, 'rotation_title', str(entry.get('title', '')))[:12]}"
        updated['hash'] = _token(key, 'rotation_hash', bookmark_id)[:12]
        obfuscated.append(updated)
    return obfuscated
