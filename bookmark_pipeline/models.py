from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


VisibilityFlag = str
BookmarkStatus = str


@dataclass(slots=True)
class BookmarkRecord:
    bookmark_id: str
    title: str
    url: str
    normalized_url: str
    domain: str
    taxonomy_category: str
    taxonomy_subcategory: str
    taxonomy_leaf: str
    tags: list[str]
    tag_confidence: dict[str, int]
    visibility_flag: VisibilityFlag
    status: BookmarkStatus
    source_browser: str
    source_path: str
    date_added: str
    last_seen: str
    classification_confidence: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedBookmark:
    title: str
    url: str
    folder_path: str
    source_browser: str
    date_added: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DuplicateEntry:
    title: str
    firefox_url: str
    matched_chrome_title: str
    matched_chrome_url: str
    duplicate_reason: str
    confidence_score: int
    firefox_folder_path: str
    chrome_folder_path: str


@dataclass(slots=True)
class TaxonomyMappingEntry:
    bookmark_title: str
    url: str
    original_firefox_path: str
    assigned_category: str
    assigned_subcategory: str
    assigned_leaf: str
    classification_confidence: int


@dataclass(slots=True)
class ReviewQueueEntry:
    bookmark_id: str
    title: str
    url: str
    reason: str
    created_at: str
    source_path: str


@dataclass(slots=True)
class RotationEntry:
    bookmark_id: str
    title: str
    hash: str
    display_week: str
    display_date: str
    display_count: int


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
