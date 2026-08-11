from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def _normalize(item: Any) -> Any:
    if is_dataclass(item):
        return asdict(item)
    if isinstance(item, dict):
        return {key: _normalize(value) for key, value in sorted(item.items())}
    if isinstance(item, list):
        return [_normalize(value) for value in item]
    return item


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize(payload)
    with path.open('w', encoding='utf-8', newline='\n') as handle:
        json.dump(normalized, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write('\n')
