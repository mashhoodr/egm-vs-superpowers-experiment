"""Link a negative scan at one location to the matching positive scan elsewhere."""
from __future__ import annotations

from stockmerge.model import Scan

WINDOW_MINUTES = 120


def scan_order(scan: Scan) -> tuple:
    return (scan.minute, scan.location, scan.export_index, scan.line)


def link_moves(scans: list[Scan]) -> dict[tuple[int, int], str]:
    positives: dict[tuple[str, int], list[Scan]] = {}
    for scan in sorted((s for s in scans if s.qty_each > 0), key=scan_order):
        positives.setdefault((scan.sku_key, scan.qty_each), []).append(scan)

    paired: set[tuple[int, int]] = set()
    moves: dict[tuple[int, int], str] = {}
    for neg in sorted((s for s in scans if s.qty_each < 0), key=scan_order):
        best, best_gap = None, None
        for pos in positives.get((neg.sku_key, -neg.qty_each), []):
            if pos.input_order in paired or pos.location == neg.location:
                continue
            gap = abs(pos.minute - neg.minute).total_seconds() / 60
            if gap > WINDOW_MINUTES:
                continue
            if best_gap is None or gap < best_gap:
                best, best_gap = pos, gap
        if best is not None:
            move_id = f"M{len(moves) // 2 + 1}"
            paired.add(best.input_order)
            moves[neg.input_order] = move_id
            moves[best.input_order] = move_id
    return moves
