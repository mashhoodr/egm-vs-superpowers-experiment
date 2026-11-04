"""Duplicate removal by max count per export."""

from __future__ import annotations

from collections import Counter

from txmerge.model import Record


def dedup(records: list[Record]) -> list[Record]:
    """Keep, per duplicate key, as many records as the largest count in any one export."""
    count: Counter = Counter()
    for record in records:
        count[(record.export_index, record.dedup_key())] += 1
    limit: dict = {}
    for (_, key), n in count.items():
        if n > limit.get(key, 0):
            limit[key] = n
    kept_count: Counter = Counter()
    kept: list[Record] = []
    for record in records:
        key = record.dedup_key()
        if kept_count[key] < limit[key]:
            kept_count[key] += 1
            kept.append(record)
    return kept
