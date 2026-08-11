from __future__ import annotations

import hashlib
import random
import sqlite3
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, datetime
from typing import Callable

from .models import BookmarkRecord, RotationEntry


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

    pool = [rec for rec in records if rec.visibility_flag == 'PUBLIC' and rec.status == 'ACTIVE']
    candidates = [
        rec for rec in pool if not (weeks_by_bookmark.get(rec.bookmark_id, set()) & recent)
    ]
    if len(candidates) < cycle_size:
        candidates = pool

    shuffled = candidates[:]
    randomizer.shuffle(shuffled)
    default_weight = lambda rec, count: 1.0 / (1 + count)  # noqa: E731
    scorer = weight_strategy or default_weight

    sorted_pool = sorted(
        shuffled,
        key=lambda rec: (
            counts.get(rec.bookmark_id, 0),
            -scorer(rec, counts.get(rec.bookmark_id, 0)),
            rec.title.lower(),
        ),
    )

    if not category_targets:
        selected = sorted_pool[:cycle_size]
    else:
        selected = []
        per_category: Counter[str] = Counter()
        for rec in sorted_pool:
            target = category_targets.get(rec.taxonomy_category, 0)
            if target and per_category[rec.taxonomy_category] >= target:
                continue
            selected.append(rec)
            per_category[rec.taxonomy_category] += 1
            if len(selected) >= cycle_size:
                break

        if len(selected) < cycle_size:
            used = {rec.bookmark_id for rec in selected}
            for rec in sorted_pool:
                if rec.bookmark_id in used:
                    continue
                selected.append(rec)
                if len(selected) >= cycle_size:
                    break

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
