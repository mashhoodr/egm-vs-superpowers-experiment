"""Collapse duplicates caused by overlapping exports of the same account."""
from collections import Counter
from dataclasses import replace

from txmerge.model import Transaction


def normalise(description: str) -> str:
    return " ".join(description.split()).casefold()


def _key(t: Transaction):
    # Decimal("-3.5") == Decimal("-3.50") and they hash equal, so scale is ignored.
    return (t.account, t.date, t.amount, normalise(t.description))


def dedupe(rows: list[Transaction]) -> list[Transaction]:
    ordered = sorted(rows, key=lambda r: r.source)
    per_file: Counter = Counter()
    first_text: dict = {}
    for r in ordered:
        k = _key(r)
        per_file[(k, r.source[0])] += 1
        first_text.setdefault(k, r.description)
    keep: Counter = Counter()
    for (k, _file), n in per_file.items():
        keep[k] = max(keep[k], n)

    out: list[Transaction] = []
    taken: Counter = Counter()
    for r in ordered:
        k = _key(r)
        if taken[k] < keep[k]:
            taken[k] += 1
            out.append(replace(r, description=first_text[k]))
    return out
