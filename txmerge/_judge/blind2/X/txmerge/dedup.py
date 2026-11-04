"""Overlap removal (D1-D4)."""

from __future__ import annotations

from dataclasses import replace

from .model import Row, row_key


def deduplicate(rows: list[Row]) -> list[Row]:
    """Keep each key as many times as its highest count in any one export.

    Output order is unspecified; the caller sorts.
    """
    ordered = sorted(rows, key=lambda r: (r.arg_index, r.line_no))

    # Steps 1-2: per-export counts, then max per key (accounts are in the key).
    per_export: dict[tuple, dict[int, int]] = {}
    for r in ordered:
        counts = per_export.setdefault(row_key(r), {})
        counts[r.arg_index] = counts.get(r.arg_index, 0) + 1
    target = {key: max(counts.values()) for key, counts in per_export.items()}

    # Steps 3-4: keep earliest occurrences, all with the first occurrence's text.
    kept_count: dict[tuple, int] = {}
    first_text: dict[tuple, str] = {}
    kept: list[Row] = []
    for r in ordered:
        key = row_key(r)
        first_text.setdefault(key, r.description)
        if kept_count.get(key, 0) < target[key]:
            kept_count[key] = kept_count.get(key, 0) + 1
            kept.append(replace(r, description=first_text[key]))
    return kept
