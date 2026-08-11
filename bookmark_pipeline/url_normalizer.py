from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_KEYS = {
    'fbclid',
    'gclid',
    'mc_cid',
    'mc_eid',
    'ref',
    'source',
    'igshid',
}

UTM_PREFIX = 'utm_'
DEFAULT_PORTS = {'http': '80', 'https': '443'}


def normalize_url(url: str) -> str:
    raw = (url or '').strip()
    if not raw:
        return ''
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', raw):
        raw = 'https://' + raw

    split = urlsplit(raw)
    scheme = split.scheme.lower() or 'https'
    hostname = (split.hostname or '').lower()
    if not hostname:
        return raw.rstrip('/')

    port = split.port
    has_default_port = port is not None and str(port) == DEFAULT_PORTS.get(scheme)
    netloc = hostname
    if port is not None and not has_default_port:
        netloc = f'{hostname}:{port}'

    path = split.path or '/'
    if path != '/' and path.endswith('/'):
        path = path.rstrip('/')

    filtered_query_parts: list[tuple[str, str]] = []
    for key, value in parse_qsl(split.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered.startswith(UTM_PREFIX) or lowered in TRACKING_KEYS:
            continue
        filtered_query_parts.append((key, value))

    filtered_query = urlencode(filtered_query_parts, doseq=True)
    return urlunsplit((scheme, netloc, path, filtered_query, ''))


def domain_from_url(url: str) -> str:
    try:
        return urlsplit(url).hostname or ''
    except ValueError:
        return ''
