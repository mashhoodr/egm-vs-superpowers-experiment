"""Dedup of copies across exports of one location (R5.1 to R5.6)."""

from __future__ import annotations

from collections import Counter

from stockmerge.model import Scan, input_order, scan_key


def dedup(scans: list[Scan]) -> tuple[list[Scan], int]:
    ordered = sorted(scans, key=input_order)
    per_export = Counter((scan_key(s), s.arg_index) for s in ordered)
    highest: dict[tuple, int] = {}
    for (key, _arg), n in per_export.items():
        if n > highest.get(key, 0):
            highest[key] = n
    seen: Counter = Counter()
    kept: list[Scan] = []
    for s in ordered:
        key = scan_key(s)
        if seen[key] < highest[key]:
            kept.append(s)
        seen[key] += 1
    return kept, len(ordered) - len(kept)
