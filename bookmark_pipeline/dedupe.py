from __future__ import annotations

import itertools
from dataclasses import dataclass
from difflib import SequenceMatcher

from .models import DuplicateEntry, ParsedBookmark
from .url_normalizer import domain_from_url, normalize_url

try:
    from rapidfuzz.fuzz import ratio as fuzz_ratio  # type: ignore
except Exception:  # pragma: no cover
    fuzz_ratio = None


@dataclass(slots=True)
class DedupeResult:
    kept_firefox: list[ParsedBookmark]
    duplicate_log: list[DuplicateEntry]


def _text_ratio(a: str, b: str) -> int:
    if fuzz_ratio is not None:
        return int(fuzz_ratio(a, b))
    return int(SequenceMatcher(a=a, b=b).ratio() * 100)


def _confidence(a: ParsedBookmark, b: ParsedBookmark) -> tuple[int, str]:
    if a.url == b.url:
        return 100, 'exact_url'
    a_norm = normalize_url(a.url)
    b_norm = normalize_url(b.url)
    if a_norm == b_norm:
        return 97, 'normalized_url'

    url_score = _text_ratio(a_norm, b_norm)
    title_score = _text_ratio(a.title.lower(), b.title.lower())
    domain_score = 100 if domain_from_url(a_norm) == domain_from_url(b_norm) else 40
    weighted = int((url_score * 0.5) + (title_score * 0.3) + (domain_score * 0.2))
    return weighted, 'fuzzy'


def dedupe_firefox_against_chrome(
    chrome: list[ParsedBookmark],
    firefox: list[ParsedBookmark],
) -> DedupeResult:
    exact_index = {bookmark.url: bookmark for bookmark in chrome}
    normalized_index = {normalize_url(bookmark.url): bookmark for bookmark in chrome}

    kept: list[ParsedBookmark] = []
    duplicate_log: list[DuplicateEntry] = []

    for candidate in firefox:
        matched: ParsedBookmark | None = None
        reason = ''
        confidence = 0

        if candidate.url in exact_index:
            matched = exact_index[candidate.url]
            reason = 'exact_url'
            confidence = 100
        else:
            norm = normalize_url(candidate.url)
            if norm in normalized_index:
                matched = normalized_index[norm]
                reason = 'normalized_url'
                confidence = 97
            else:
                domain = domain_from_url(norm)
                pool = [b for b in chrome if domain_from_url(normalize_url(b.url)) == domain]
                for probe in itertools.islice(pool, 0, 200):
                    score, stage = _confidence(candidate, probe)
                    if score > confidence:
                        confidence = score
                        reason = stage
                        matched = probe
                if confidence < 75:
                    matched = None

        if matched is None:
            kept.append(candidate)
            continue

        duplicate_log.append(
            DuplicateEntry(
                title=candidate.title,
                firefox_url=candidate.url,
                matched_chrome_title=matched.title,
                matched_chrome_url=matched.url,
                duplicate_reason=reason,
                confidence_score=confidence,
                firefox_folder_path=candidate.folder_path,
                chrome_folder_path=matched.folder_path,
            )
        )

    return DedupeResult(kept_firefox=kept, duplicate_log=duplicate_log)
