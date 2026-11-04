"""Output ordering and transfer pairing between the user's own accounts."""
from collections import defaultdict

from txmerge.model import Transaction

WINDOW_DAYS = 3


def sort_key(t: Transaction):
    return (t.date, t.account, t.source)


def order(rows: list[Transaction]) -> list[Transaction]:
    return sorted(rows, key=sort_key)


def pair_transfers(ordered: list[Transaction]) -> list[str]:
    ids = [""] * len(ordered)
    inflows_by_amount: dict = defaultdict(list)  # amount -> [index, ...] in output order
    for j, row in enumerate(ordered):
        if row.amount > 0:
            inflows_by_amount[row.amount].append(j)

    next_id = 1
    for i, out in enumerate(ordered):
        if out.amount >= 0:
            continue
        best = None  # (day_diff, index)
        for j in inflows_by_amount.get(-out.amount, ()):
            cand = ordered[j]
            if ids[j] or cand.account == out.account:
                continue
            diff = abs((cand.date - out.date).days)
            if diff <= WINDOW_DAYS and (best is None or diff < best[0]):
                best = (diff, j)
        if best is not None:
            tid = f"T{next_id:04d}"
            ids[i] = ids[best[1]] = tid
            next_id += 1
    return ids
