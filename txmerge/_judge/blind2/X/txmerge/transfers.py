"""Transfer pairing (D6-D9, D17)."""

from __future__ import annotations

from decimal import Decimal

from .model import Row

MAX_GAP_DAYS = 3


def transfer_id(n: int) -> str:
    return f"T{n:04d}"


def pair_transfers(rows: list[Row]) -> list[str]:
    """Input is the sorted ledger; returns a transfer_id per position ('' if none)."""
    inflows: dict[Decimal, list[int]] = {}
    for pos, r in enumerate(rows):
        if r.amount > 0:
            inflows.setdefault(r.amount, []).append(pos)

    ids = [""] * len(rows)
    paired = [False] * len(rows)
    n = 0
    for pos, out in enumerate(rows):
        if not out.amount < 0 or paired[pos]:
            continue
        best = None
        for cand in inflows.get(-out.amount, ()):
            inflow = rows[cand]
            if paired[cand] or inflow.account == out.account:
                continue
            gap = abs((inflow.date - out.date).days)
            if gap > MAX_GAP_DAYS:
                continue
            if best is None or (gap, cand) < best:
                best = (gap, cand)
        if best is not None:
            n += 1
            tid = transfer_id(n)
            cand = best[1]
            ids[pos] = ids[cand] = tid
            paired[pos] = paired[cand] = True
    return ids
