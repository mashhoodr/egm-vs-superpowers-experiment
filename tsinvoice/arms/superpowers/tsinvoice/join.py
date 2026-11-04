"""Link entries that continue one another into sessions."""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from tsinvoice.model import Entry, Session, norm

MAX_GAP = timedelta(minutes=2)
_ZERO = timedelta(0)


def _join_key(e: Entry):
    return (norm(e.client), norm(e.description))


def join(entries: list[Entry]) -> list[Session]:
    ordered = sorted(entries, key=lambda e: (e.start, e.arg_index, e.line))
    successor: list[int | None] = [None] * len(ordered)
    has_predecessor = [False] * len(ordered)
    by_key: dict = defaultdict(list)
    for i, e in enumerate(ordered):
        by_key[_join_key(e)].append(i)

    for i, p in enumerate(ordered):
        best, best_rank = None, None
        for j in by_key[_join_key(p)]:
            if j == i or has_predecessor[j]:
                continue
            q = ordered[j]
            gap = q.start - p.end
            if _ZERO <= gap <= MAX_GAP:
                rank = (gap, q.arg_index, q.line)
                if best_rank is None or rank < best_rank:
                    best, best_rank = j, rank
        if best is not None:
            successor[i] = best
            has_predecessor[best] = True

    sessions = []
    for i in range(len(ordered)):
        if has_predecessor[i]:
            continue
        chain, k = [], i
        while k is not None:
            chain.append(ordered[k])
            k = successor[k]
        sessions.append(Session(chain))
    return sessions
