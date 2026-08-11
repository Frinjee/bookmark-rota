from __future__ import annotations

import hashlib
from dataclasses import asdict
from datetime import date

from .classifier import classify_bookmark
from .models import BookmarkRecord, ParsedBookmark, ReviewQueueEntry, TaxonomyMappingEntry
from .private_markers import PRIVATE_DOMAINS, PRIVATE_FOLDERS, PRIVATE_KEYWORDS
from .taxonomy import UNSORTED_CATEGORY, classify_from_path
from .tagger import generate_tags
from .url_normalizer import domain_from_url, normalize_url


def _bookmark_id(title: str, normalized_url: str) -> str:
    payload = f'{title.strip().lower()}|{normalized_url.strip().lower()}'
    digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    return digest[:16]


_REVIEW_MARKERS: tuple[str, ...] = (
    'drive.google.com',
    'onedrive',
    'dropbox',
    'resume',
    'application',
)


def _visibility_for_bookmark(title: str, url: str, folder_path: str) -> str:
    blob = f'{title} {url} {folder_path}'.lower()
    domain = domain_from_url(normalize_url(url))
    folder_lower = folder_path.lower()

    if (
        any(kw in blob for kw in PRIVATE_KEYWORDS)
        or domain in PRIVATE_DOMAINS
        or any(pf in folder_lower for pf in PRIVATE_FOLDERS)
    ):
        return 'PRIVATE'
    if any(marker in blob for marker in _REVIEW_MARKERS):
        return 'REVIEW'
    return 'PUBLIC'


def build_catalog(
    chrome: list[ParsedBookmark],
    firefox_kept: list[ParsedBookmark],
) -> tuple[list[BookmarkRecord], list[TaxonomyMappingEntry], list[ReviewQueueEntry]]:
    records: list[BookmarkRecord] = []
    mapping_log: list[TaxonomyMappingEntry] = []
    review_queue: list[ReviewQueueEntry] = []
    today = date.today().isoformat()

    all_bookmarks = [*chrome, *firefox_kept]
    for bookmark in all_bookmarks:
        normalized = normalize_url(bookmark.url)
        domain = domain_from_url(normalized)

        inferred = classify_from_path(bookmark.folder_path)
        if inferred is None:
            classification = classify_bookmark(
                title=bookmark.title,
                normalized_url=normalized,
                domain=domain,
                folder_path=bookmark.folder_path,
            )
            category, subcategory, leaf = (
                classification.category,
                classification.subcategory,
                classification.leaf,
            )
            confidence = classification.confidence
        else:
            category, subcategory, leaf = inferred
            confidence = 96 if bookmark.source_browser == 'chrome' else 88
            classification = classify_bookmark(
                title=bookmark.title,
                normalized_url=normalized,
                domain=domain,
                folder_path=bookmark.folder_path,
            )

        tags, tag_conf = generate_tags(
            classification,
            title=bookmark.title,
            domain=domain,
            url=normalized,
        )
        bookmark_id = _bookmark_id(bookmark.title, normalized)
        visibility = _visibility_for_bookmark(bookmark.title, bookmark.url, bookmark.folder_path)

        record = BookmarkRecord(
            bookmark_id=bookmark_id,
            title=bookmark.title,
            url=bookmark.url,
            normalized_url=normalized,
            domain=domain,
            taxonomy_category=category,
            taxonomy_subcategory=subcategory,
            taxonomy_leaf=leaf,
            tags=tags,
            tag_confidence=tag_conf,
            visibility_flag=visibility,
            status='ACTIVE',
            source_browser=bookmark.source_browser,
            source_path=bookmark.folder_path,
            date_added=bookmark.date_added or today,
            last_seen=today,
            classification_confidence=confidence,
            metadata=bookmark.metadata,
        )
        records.append(record)

        if bookmark.source_browser == 'firefox':
            mapping_log.append(
                TaxonomyMappingEntry(
                    bookmark_title=bookmark.title,
                    url=bookmark.url,
                    original_firefox_path=bookmark.folder_path,
                    assigned_category=record.taxonomy_category,
                    assigned_subcategory=record.taxonomy_subcategory,
                    assigned_leaf=record.taxonomy_leaf,
                    classification_confidence=record.classification_confidence,
                )
            )

        if record.taxonomy_category == UNSORTED_CATEGORY or record.visibility_flag == 'REVIEW':
            review_queue.append(
                ReviewQueueEntry(
                    bookmark_id=record.bookmark_id,
                    title=record.title,
                    url=record.url,
                    reason=(
                        'taxonomy_unmatched'
                        if record.taxonomy_category == UNSORTED_CATEGORY
                        else 'review_visibility'
                    ),
                    created_at=today,
                    source_path=record.source_path,
                )
            )

    unique: dict[str, BookmarkRecord] = {}
    for record in records:
        # keep chrome canonical when records collapse on the same identity
        existing = unique.get(record.bookmark_id)
        if existing is None or (
            existing.source_browser != 'chrome' and record.source_browser == 'chrome'
        ):
            unique[record.bookmark_id] = record

    sorted_records = sorted(
        unique.values(),
        key=lambda item: (
            item.taxonomy_category,
            item.taxonomy_subcategory,
            item.taxonomy_leaf,
            item.title.lower(),
            item.url,
        ),
    )
    return sorted_records, mapping_log, review_queue


def bookmark_record_to_dict(record: BookmarkRecord) -> dict[str, object]:
    return asdict(record)
