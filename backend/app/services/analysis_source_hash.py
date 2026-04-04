"""
Детерминированный отпечаток значимых секций анкеты для MVP актуализации анализа.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

TRACKED_SECTIONS: tuple[str, ...] = (
    "assets",
    "business_processes",
    "incidents",
    "access_matrix",
)


def _canonical_json_fragment(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def compute_analysis_source_hash(response_data: dict[str, Any]) -> str:
    """
    SHA-256 по объекту {section: response_data[section]} для отслеживаемых ключей.
    Отсутствующие ключи трактуются как пустые списки.
    """
    payload: dict[str, Any] = {}
    for key in TRACKED_SECTIONS:
        raw = response_data.get(key)
        if isinstance(raw, list):
            payload[key] = raw
        else:
            payload[key] = []
    body = _canonical_json_fragment(payload)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
