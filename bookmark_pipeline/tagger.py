from __future__ import annotations

from .classifier import ClassificationResult
from .private_markers import PRIVATE_DOMAINS, PRIVATE_KEYWORDS


def generate_tags(
    classification: ClassificationResult,
    *,
    title: str,
    domain: str,
    url: str = '',
) -> tuple[list[str], dict[str, int]]:
    tags: list[str] = []
    confidence: dict[str, int] = {}

    for tag in [classification.category, classification.subcategory, classification.leaf]:
        if tag:
            tags.append(tag)
            confidence[tag] = classification.confidence

    lowered = f'{title} {domain} {url}'.lower()
    if 'search' in lowered:
        tags.append('SEARCH_ENGINE')
        confidence['SEARCH_ENGINE'] = min(100, classification.confidence + 4)
    if 'github' in lowered:
        tags.append('GITHUB')
        confidence['GITHUB'] = min(100, classification.confidence + 2)
    if 'privacy' in lowered:
        tags.append('PRIVACY_TOPIC')
        confidence['PRIVACY_TOPIC'] = min(100, classification.confidence + 3)

    if any(kw in lowered for kw in PRIVATE_KEYWORDS) or domain in PRIVATE_DOMAINS:
        tags.append('PRIVATE_PERSONAL')
        confidence['PRIVATE_PERSONAL'] = 95

    deduped_tags = sorted(set(tags))
    ordered_confidence = {tag: confidence[tag] for tag in deduped_tags}
    return deduped_tags, ordered_confidence
