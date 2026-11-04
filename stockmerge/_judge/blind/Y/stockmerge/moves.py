"""Move linking (R6.1 to R6.5)."""

from __future__ import annotations

from collections import defaultdict

from stockmerge.model import MOVE_WINDOW_MINUTES, Scan, scan_order


def minutes_between(a: Scan, b: Scan) -> int:
    return abs(int((a.minute - b.minute).total_seconds()) // 60)


def link_moves(scans: list[Scan]) -> dict[tuple[int, int], str]:
    groups: dict[tuple[str, int], list[Scan]] = defaultdict(list)
    for s in scans:
        if s.qty_each > 0:
            groups[(s.sku_norm, s.qty_each)].append(s)
    for group in groups.values():
        group.sort(key=scan_order)
    negatives = sorted((s for s in scans if s.qty_each < 0), key=scan_order)
    used: set[tuple[int, int]] = set()
    move_ids: dict[tuple[int, int], str] = {}
    n = 0
    for neg in negatives:
        candidates = [
            p
            for p in groups.get((neg.sku_norm, -neg.qty_each), [])
            if p.ident not in used
            and p.location != neg.location
            and minutes_between(neg, p) <= MOVE_WINDOW_MINUTES
        ]
        if not candidates:
            continue
        partner = min(candidates, key=lambda p: (minutes_between(neg, p), scan_order(p)))
        used.add(partner.ident)
        n += 1
        move_id = f"M{n:04d}"
        move_ids[neg.ident] = move_id
        move_ids[partner.ident] = move_id
    return move_ids
