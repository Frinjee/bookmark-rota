"""Hosts that must never appear on the public website rota feed.

Catalog records stay PUBLIC/ACTIVE; they are only excluded from rotation
candidates and from bookmarks_rota.json. Do not keyword-match '4chan' in
titles or paths (archive.org / wiki pages about 4chan stay eligible).
"""
from __future__ import annotations

from .url_normalizer import domain_from_url, normalize_url

# Registrable domains: exact host or any subdomain.
SITE_FEED_BLOCKED_SUFFIX_DOMAINS: frozenset[str] = frozenset({
    '4chan.org',
    '4channel.org',
    '4cdn.org',
    '4chansearch.com',
})


def is_blocked_site_feed_host(host: str) -> bool:
    hostname = (host or '').lower().strip('.')
    if not hostname:
        return False
    for blocked in SITE_FEED_BLOCKED_SUFFIX_DOMAINS:
        if hostname == blocked or hostname.endswith('.' + blocked):
            return True
    return False


def is_blocked_site_feed_url(url: str) -> bool:
    return is_blocked_site_feed_host(domain_from_url(normalize_url(url)))
