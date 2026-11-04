"""Transfer pairing between accounts."""

from __future__ import annotations

from txmerge.model import TRANSFER_CATEGORY, TRANSFER_WINDOW_DAYS, Record


def pair_transfers(records: list[Record]) -> int:
    """Greedily pair outflows with inflows; records must be in output order."""
    index: dict = {}
    for pos, record in enumerate(records):
        if record.amount > 0:
            index.setdefault(record.amount, []).append(pos)
    pairs = 0
    for outflow in records:
        if outflow.amount >= 0 or outflow.transfer_id:
            continue
        best = None
        for pos in index.get(-outflow.amount, []):
            inflow = records[pos]
            if inflow.transfer_id or inflow.account == outflow.account:
                continue
            gap = abs((inflow.date - outflow.date).days)
            if gap > TRANSFER_WINDOW_DAYS:
                continue
            candidate = (gap, pos)
            if best is None or candidate < best:
                best = candidate
        if best is not None:
            pairs += 1
            tid = f"T{pairs:04d}"
            inflow = records[best[1]]
            for r in (outflow, inflow):
                r.transfer_id = tid
                r.category = TRANSFER_CATEGORY
    return pairs
