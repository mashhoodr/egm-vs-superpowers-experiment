"""Pure merge logic (Stages 4-8). No I/O."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal, localcontext

from tsinvoice.model import Entry, OutputRow, Rule, Session

MAX_GAP = timedelta(minutes=2)


def dedupe(entries: list[Entry]) -> list[Entry]:
    """Stage 4: keep, per duplicate key, the largest per-export count."""
    ordered = sorted(entries, key=lambda e: e.order)
    per_export: Counter = Counter((e.dup_key, e.order[0]) for e in ordered)
    largest: dict = {}
    for (key, _export), count in per_export.items():
        largest[key] = max(largest.get(key, 0), count)
    kept_count: Counter = Counter()
    kept: list[Entry] = []
    for e in ordered:
        if kept_count[e.dup_key] < largest[e.dup_key]:
            kept_count[e.dup_key] += 1
            kept.append(e)
    return kept


def join(entries: list[Entry]) -> list[Session]:
    """Stage 5: greedy join of continuations within client+description."""
    groups: dict[tuple[str, str], list[Entry]] = defaultdict(list)
    for e in sorted(entries, key=lambda e: e.order):
        groups[(e.client_key, e.desc_key)].append(e)

    sessions: list[Session] = []
    for key in sorted(groups):
        group = sorted(groups[key], key=lambda e: (e.start, e.order))
        has_pred = [False] * len(group)
        succ: list[int | None] = [None] * len(group)
        for i, p in enumerate(group):
            best = None
            for j, q in enumerate(group):
                if has_pred[j]:
                    continue
                gap = q.start - p.end
                if timedelta(0) <= gap <= MAX_GAP:
                    cand = (gap, q.order, j)
                    if best is None or cand < best:
                        best = cand
            if best is not None:
                succ[i] = best[2]
                has_pred[best[2]] = True
        for i in range(len(group)):
            if has_pred[i]:
                continue
            chain = [group[i]]
            nxt = succ[i]
            while nxt is not None:
                chain.append(group[nxt])
                nxt = succ[nxt]
            sessions.append(Session(entries=chain))
    return sessions


def find_rate(rules: list[Rule], entry: Entry) -> Decimal | None:
    """Stage 6: first rule whose pattern is in the client or description."""
    for rule in rules:
        if rule.pattern_key in entry.client_key or rule.pattern_key in entry.desc_key:
            return rule.rate
    return None


def price(minutes: int, rate: Decimal) -> str:
    """Stage 6: minutes x rate / 60, half-up to 2 places, no exponent."""
    with localcontext() as ctx:
        ctx.prec = 50
        amount = (Decimal(minutes) * rate / Decimal(60)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return format(amount, "f")


def _is_exact_repeat(a: Session, b: Session) -> bool:
    return (
        len(a.entries) == 1
        and len(b.entries) == 1
        and a.first.dup_key == b.first.dup_key
    )


def merge(
    entries: list[Entry], rules: list[Rule]
) -> tuple[list[OutputRow], list[str]]:
    """Stages 4-8: return sorted rows, then unrated and overlap warnings."""
    sessions = join(dedupe(entries))
    sessions.sort(key=lambda s: (s.first.client_key, s.start, s.first.order))

    rows: list[OutputRow] = []
    unrated: list[str] = []
    next_id = 1
    for s in sessions:
        first = s.first
        date = first.start.date().isoformat()
        minutes = s.billed_minutes
        rate = find_rate(rules, first)
        if rate is None:
            amount = "0.00"
            unrated.append(
                f"tsinvoice: warning: no rate for client '{first.client}' "
                f"description '{first.description}' on {date}"
            )
        else:
            amount = price(minutes, rate)
        session_id = ""
        if len(s.entries) > 1:
            session_id = f"S{next_id}"
            next_id += 1
        rows.append(
            OutputRow(
                date=date,
                client=first.client,
                description=first.description,
                minutes=minutes,
                amount=amount,
                session_id=session_id,
                session=s,
            )
        )

    overlaps: list[str] = []
    for i, a in enumerate(rows):
        for j in range(i + 1, len(rows)):
            b = rows[j]
            sa, sb = a.session, b.session
            if sa.first.client_key != sb.first.client_key:
                continue
            if not (sa.start < sb.end and sb.start < sa.end):
                continue
            if _is_exact_repeat(sa, sb):
                continue
            overlaps.append(
                f"tsinvoice: warning: overlapping sessions for client "
                f"'{a.client}': row {i + 1} and row {j + 1}"
            )
    return rows, unrated + overlaps
