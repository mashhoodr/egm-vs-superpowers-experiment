"""Remove scans duplicated by overlapping exports of the same location."""
from __future__ import annotations

from stockmerge.model import Scan


def dedupe(scans: list[Scan]) -> list[Scan]:
    groups: dict[tuple, dict[int, list[Scan]]] = {}
    for scan in sorted(scans, key=lambda s: s.input_order):
        key = (scan.location, scan.minute, scan.sku_key, scan.qty_each)
        groups.setdefault(key, {}).setdefault(scan.export_index, []).append(scan)

    kept: list[Scan] = []
    for by_export in groups.values():
        exports = sorted(by_export)
        most = max(len(copies) for copies in by_export.values())
        for k in range(most):
            source = next(e for e in exports if len(by_export[e]) > k)
            kept.append(by_export[source][k])
    return sorted(kept, key=lambda s: s.input_order)
