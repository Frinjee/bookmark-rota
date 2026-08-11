from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from .taxonomy import (
    CANONICAL_TAXONOMY,
    UNSORTED_CATEGORY,
    UNSORTED_LEAF,
    UNSORTED_SUBCATEGORY,
)


@dataclass(slots=True)
class ClassificationResult:
    category: str
    subcategory: str
    leaf: str
    confidence: int
    reasons: list[str]


_RULES: list[tuple[re.Pattern[str], tuple[str, str, str], int]] = [
    (re.compile(r'\bosint|dork|shodan|inteltechniques|bellingcat\b', re.I), ('INFSEC', 'OSINT', 'SEARCH'), 92),
    (re.compile(r'\bdfir|forensics|volatility|android forensics|ios forensics\b', re.I), ('INFSEC', 'DFIR', 'TOOLS'), 90),
    (re.compile(r'\bburp|xss|sqli|injection|ctf|hackthebox|tryhackme\b', re.I), ('INFSEC', 'PENTEST', 'WEB'), 89),
    (re.compile(r'\bprivacy|opsec|dehashed|have i been pwned|protonmail\b', re.I), ('PRIVACY', 'OPSEC', ''), 91),
    (re.compile(r'\bpython|pypi|jupyter\b', re.I), ('DEV', 'PYTHON', ''), 88),
    (re.compile(r'\bjavascript|css|html|webdev|react|vue|svelte\b', re.I), ('DEV', 'WEBDEV', ''), 86),
    (re.compile(r'\blinux|ubuntu|kali|shell|bash\b', re.I), ('DEV', 'LINUX', ''), 86),
    (re.compile(r'\bsql|sqlite|postgres|database\b', re.I), ('DEV', 'DATABASES', ''), 86),
    (re.compile(r'\bminecraft\b', re.I), ('GAMING', 'MINECRAFT', ''), 95),
    (re.compile(r'\bteamfight|tft\b', re.I), ('GAMING', 'TFT', ''), 95),
    (re.compile(r'\bpath of exile|poe\b', re.I), ('GAMING', 'ARPG', ''), 94),
    (re.compile(r'\bdestiny\b', re.I), ('GAMING', 'FPS', ''), 90),
    (re.compile(r'\blost ark\b', re.I), ('GAMING', 'MMO', ''), 90),
    (re.compile(r'\bbaltimore|archives|museum|genealogy\b', re.I), ('RESEARCH', 'BALTIMORE', ''), 88),
    (re.compile(r'\bcourse|university|ubalt|history\b', re.I), ('EDUCATION', 'COURSES', ''), 84),
    (re.compile(r'\bjob|interview|resume|portfolio\b', re.I), ('CAREER', 'JOB_SEARCH', ''), 86),
    (re.compile(r'\bmovie|netflix|stream|podcast|music|radio\b', re.I), ('MEDIA', 'STREAMING', ''), 84),
    (re.compile(r'\brecipe|cooking|food\b', re.I), ('PERSONAL', 'RECIPES', ''), 89),
    (re.compile(r'\bbookmarklet|cheat sheet|calculator|tools?\b', re.I), ('UTILITIES', 'TOOLS', ''), 80),
]


def _validate(category: str, subcategory: str, leaf: str) -> tuple[str, str, str]:
    if category == UNSORTED_CATEGORY:
        return category, subcategory, leaf
    if category not in CANONICAL_TAXONOMY:
        return UNSORTED_CATEGORY, UNSORTED_SUBCATEGORY, UNSORTED_LEAF
    if subcategory and subcategory not in CANONICAL_TAXONOMY[category]:
        return UNSORTED_CATEGORY, UNSORTED_SUBCATEGORY, UNSORTED_LEAF
    if leaf and leaf not in CANONICAL_TAXONOMY[category].get(subcategory, []):
        return UNSORTED_CATEGORY, UNSORTED_SUBCATEGORY, UNSORTED_LEAF
    return category, subcategory, leaf


def classify_bookmark(
    *,
    title: str,
    normalized_url: str,
    domain: str,
    folder_path: str,
    llm_classifier: Callable[[dict[str, str]], dict[str, object] | None] | None = None,
) -> ClassificationResult:
    blob = ' '.join([title, normalized_url, domain, folder_path]).strip()
    best: tuple[str, str, str] | None = None
    confidence = 0
    reasons: list[str] = []

    for pattern, assignment, score in _RULES:
        if pattern.search(blob):
            if score > confidence:
                best = assignment
                confidence = score
            reasons.append(f'rule:{pattern.pattern}')

    if best is None and llm_classifier is not None:
        llm_result = llm_classifier(
            {
                'title': title,
                'normalized_url': normalized_url,
                'domain': domain,
                'folder_path': folder_path,
            }
        )
        if isinstance(llm_result, dict):
            category = llm_result.get('category', UNSORTED_CATEGORY)
            subcategory = llm_result.get('subcategory', UNSORTED_SUBCATEGORY)
            leaf = llm_result.get('leaf', UNSORTED_LEAF)
            confidence = int(llm_result.get('confidence', 50))
            category, subcategory, leaf = _validate(category, subcategory, leaf)
            return ClassificationResult(
                category=category,
                subcategory=subcategory,
                leaf=leaf,
                confidence=confidence,
                reasons=['llm_fallback'],
            )

    if best is None:
        return ClassificationResult(
            category=UNSORTED_CATEGORY,
            subcategory=UNSORTED_SUBCATEGORY,
            leaf=UNSORTED_LEAF,
            confidence=50,
            reasons=['no_match'],
        )

    category, subcategory, leaf = _validate(*best)
    if category == UNSORTED_CATEGORY:
        return ClassificationResult(
            category=category,
            subcategory=subcategory,
            leaf=leaf,
            confidence=55,
            reasons=['invalid_assignment'],
        )

    return ClassificationResult(
        category=category,
        subcategory=subcategory,
        leaf=leaf,
        confidence=confidence,
        reasons=reasons,
    )
