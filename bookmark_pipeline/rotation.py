from __future__ import annotations

import hashlib
import random
import sqlite3
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, datetime
from typing import Callable

from .models import BookmarkRecord, RotationEntry
from .site_feed_blocklist import is_blocked_site_feed_host, is_blocked_site_feed_url


def iso_week_key(run_date: date) -> str:
    year, week, _ = run_date.isocalendar()
    return f'{year}-W{week:02d}'


def load_display_counts(conn: sqlite3.Connection) -> tuple[Counter[str], dict[str, set[str]]]:
    counts: Counter[str] = Counter()
    weeks_by_bookmark: dict[str, set[str]] = defaultdict(set)
    rows = conn.execute(
        'SELECT bookmark_id, display_week, display_count FROM bookmark_display_history'
    ).fetchall()
    for bookmark_id, week, display_count in rows:
        counts[bookmark_id] += int(display_count)
        weeks_by_bookmark[bookmark_id].add(week)
    return counts, weeks_by_bookmark


def _recent_weeks(week_key: str, window: int) -> set[str]:
    year = int(week_key[:4])
    week = int(week_key[-2:])
    output = set()
    for offset in range(window):
        w = week - offset
        y = year
        while w <= 0:
            y -= 1
            w += 52
        output.add(f'{y}-W{w:02d}')
    return output


def select_weekly_rotation(
    records: list[BookmarkRecord],
    counts: Counter[str],
    weeks_by_bookmark: dict[str, set[str]],
    *,
    week_key: str,
    display_date: str,
    cycle_size: int = 12,
    recency_window_weeks: int = 4,
    category_targets: dict[str, int] | None = None,
    weight_strategy: Callable[[BookmarkRecord, int], float] | None = None,
) -> list[RotationEntry]:
    seed = int(hashlib.sha256(week_key.encode('utf-8')).hexdigest()[:8], 16)
    randomizer = random.Random(seed)
    recent = _recent_weeks(week_key, recency_window_weeks)

    sorted_pool = _ranked_rotation_pool(
        records,
        counts,
        weeks_by_bookmark,
        cycle_size=cycle_size,
        weight_strategy=weight_strategy,
        randomizer=randomizer,
        recent=recent,
    )
    selected = _pick_from_ranked_pool(sorted_pool, cycle_size, category_targets)
    return _entries_from_records(
        selected,
        counts,
        week_key=week_key,
        display_date=display_date,
    )


def _is_site_feed_eligible(rec: BookmarkRecord) -> bool:
    return (
        rec.visibility_flag == 'PUBLIC'
        and rec.status == 'ACTIVE'
        and not is_blocked_site_feed_host(rec.domain)
        and not is_blocked_site_feed_url(rec.url)
    )


def _ranked_rotation_pool(
    records: list[BookmarkRecord],
    counts: Counter[str],
    weeks_by_bookmark: dict[str, set[str]],
    *,
    cycle_size: int,
    weight_strategy: Callable[[BookmarkRecord, int], float] | None,
    randomizer: random.Random,
    recent: set[str],
) -> list[BookmarkRecord]:
    pool = [rec for rec in records if _is_site_feed_eligible(rec)]
    candidates = [
        rec for rec in pool if not (weeks_by_bookmark.get(rec.bookmark_id, set()) & recent)
    ]
    if len(candidates) < cycle_size:
        candidates = pool

    shuffled = candidates[:]
    randomizer.shuffle(shuffled)
    default_weight = lambda rec, count: 1.0 / (1 + count)  # noqa: E731
    scorer = weight_strategy or default_weight
    return sorted(
        shuffled,
        key=lambda rec: (
            counts.get(rec.bookmark_id, 0),
            -scorer(rec, counts.get(rec.bookmark_id, 0)),
            rec.title.lower(),
        ),
    )


def _pick_from_ranked_pool(
    sorted_pool: list[BookmarkRecord],
    cycle_size: int,
    category_targets: dict[str, int] | None,
    *,
    skip_ids: set[str] | None = None,
) -> list[BookmarkRecord]:
    blocked = skip_ids or set()
    if not category_targets:
        return [rec for rec in sorted_pool if rec.bookmark_id not in blocked][:cycle_size]

    selected: list[BookmarkRecord] = []
    per_category: Counter[str] = Counter()
    for rec in sorted_pool:
        if rec.bookmark_id in blocked:
            continue
        target = category_targets.get(rec.taxonomy_category, 0)
        if target and per_category[rec.taxonomy_category] >= target:
            continue
        selected.append(rec)
        per_category[rec.taxonomy_category] += 1
        if len(selected) >= cycle_size:
            break

    if len(selected) < cycle_size:
        used = {rec.bookmark_id for rec in selected} | blocked
        for rec in sorted_pool:
            if rec.bookmark_id in used:
                continue
            selected.append(rec)
            if len(selected) >= cycle_size:
                break
    return selected


def _entries_from_records(
    selected: list[BookmarkRecord],
    counts: Counter[str],
    *,
    week_key: str,
    display_date: str,
) -> list[RotationEntry]:
    weekly_entries: list[RotationEntry] = []
    for rec in selected:
        shown_count = counts.get(rec.bookmark_id, 0) + 1
        unique_hash = hashlib.sha256(f'{rec.bookmark_id}|{week_key}'.encode('utf-8')).hexdigest()[:12]
        weekly_entries.append(
            RotationEntry(
                bookmark_id=rec.bookmark_id,
                title=rec.title,
                hash=unique_hash,
                display_week=week_key,
                display_date=display_date,
                display_count=shown_count,
            )
        )
    return weekly_entries


def backfill_weekly_rotation(
    kept_ids: list[str],
    records: list[BookmarkRecord],
    counts: Counter[str],
    weeks_by_bookmark: dict[str, set[str]],
    *,
    week_key: str,
    display_date: str,
    cycle_size: int = 12,
    recency_window_weeks: int = 4,
    category_targets: dict[str, int] | None = None,
    weight_strategy: Callable[[BookmarkRecord, int], float] | None = None,
) -> list[RotationEntry]:
    """Keep existing weekly IDs in order and fill remaining slots from the ranked pool."""
    by_id = {rec.bookmark_id: rec for rec in records}
    selected: list[BookmarkRecord] = []
    for bookmark_id in kept_ids:
        rec = by_id.get(bookmark_id)
        if rec is None or not _is_site_feed_eligible(rec):
            continue
        selected.append(rec)

    need = cycle_size - len(selected)
    if need <= 0:
        return _entries_from_records(
            selected[:cycle_size],
            counts,
            week_key=week_key,
            display_date=display_date,
        )

    seed = int(hashlib.sha256(week_key.encode('utf-8')).hexdigest()[:8], 16)
    randomizer = random.Random(seed)
    recent = _recent_weeks(week_key, recency_window_weeks)
    ranked = _ranked_rotation_pool(
        records,
        counts,
        weeks_by_bookmark,
        cycle_size=cycle_size,
        weight_strategy=weight_strategy,
        randomizer=randomizer,
        recent=recent,
    )
    extras = _pick_from_ranked_pool(
        ranked,
        need,
        category_targets,
        skip_ids={rec.bookmark_id for rec in selected},
    )
    selected.extend(extras)
    return _entries_from_records(
        selected,
        counts,
        week_key=week_key,
        display_date=display_date,
    )


def rotation_to_json(entries: list[RotationEntry]) -> list[dict[str, object]]:
    return [asdict(item) for item in entries]


def bookmark_hashes_legacy(entries: list[RotationEntry]) -> list[dict[str, object]]:
    return [
        {
            'title': entry.title,
            'hash': entry.hash,
            'week': entry.display_week,
            'displayed_on': entry.display_date,
        }
        for entry in entries
    ]


def today_date() -> date:
    return datetime.utcnow().date()
