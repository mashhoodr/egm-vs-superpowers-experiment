"""Dedupe, join and price timesheet entries."""
from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from .parse import Entry, Rate, norm, warn

MAX_GAP = timedelta(minutes=2)
BILL_STEP = 6


def _key(e: Entry) -> tuple:
    return (e.tracker, norm(e.client), norm(e.description), e.start, e.end)


def dedupe(files: list[list[Entry]]) -> list[Entry]:
    """Remove copies that appear because exports of one tracker overlap.

    `files` is one entry list per export file. An identical entry
    (same tracker, normalised client/description, start, end) repeated inside
    one file is real repeated work, so for each key we keep as many copies as
    the single file that holds the most of them. Earliest copies are kept.
    """
    need: Counter = Counter()
    for entries in files:
        for key, count in Counter(_key(e) for e in entries).items():
            need[key] = max(need[key], count)
    kept = []
    for entries in files:
        for e in entries:
            k = _key(e)
            if need[k] > 0:
                need[k] -= 1
                kept.append(e)
    return kept


def join(entries: list[Entry]) -> list[list[Entry]]:
    """Chain entries where one starts 0-2 minutes after the other ends.

    Client and description must match (normalised). Entries are processed in
    start order; each picks the unclaimed successor with the smallest gap,
    ties broken by input order.
    """
    ordered = sorted(entries, key=lambda e: (e.start, e.order))
    by_topic = defaultdict(list)
    for e in ordered:
        by_topic[(norm(e.client), norm(e.description))].append(e)

    succ: dict[int, Entry] = {}
    has_pred: set[int] = set()
    for e in ordered:
        candidates = [
            c for c in by_topic[(norm(e.client), norm(e.description))]
            if c is not e and id(c) not in has_pred
            and e.end <= c.start <= e.end + MAX_GAP
        ]
        if candidates:
            best = min(candidates, key=lambda c: (c.start - e.end, c.order))
            succ[id(e)] = best
            has_pred.add(id(best))

    chains = []
    for e in ordered:
        if id(e) in has_pred:
            continue
        chain = [e]
        while id(chain[-1]) in succ:
            chain.append(succ[id(chain[-1])])
        chains.append(chain)
    return chains


def billed_minutes(raw: int) -> int:
    return -(-raw // BILL_STEP) * BILL_STEP


def find_rate(rates: list[Rate], client: str, description: str) -> Decimal | None:
    c, d = client.casefold(), description.casefold()
    for r in rates:
        p = r.pattern.casefold()
        if p in c or p in d:
            return r.rate
    return None


@dataclass
class Session:
    date: str
    client: str
    description: str
    minutes: int
    amount: str
    session_id: str
    sort_key: tuple


def _session_id(chain: list[Entry]) -> str:
    h = hashlib.sha256()
    for e in chain:
        h.update(repr(_key(e)).encode())
    return "S-" + h.hexdigest()[:12]


def price(chains: list[list[Entry]], rates: list[Rate]) -> list[Session]:
    sessions = []
    used_ids: Counter = Counter()
    for chain in chains:
        first = chain[0]
        minutes = billed_minutes(sum(e.minutes for e in chain))
        rate = find_rate(rates, first.client, first.description)
        if rate is None:
            warn(f"no rate matches client {first.client!r} "
                 f"description {first.description!r}; priced at 0.00")
            rate = Decimal(0)
        amount = (Decimal(minutes) / 60 * rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
        sid = ""
        if len(chain) > 1:
            sid = _session_id(chain)
            used_ids[sid] += 1
            if used_ids[sid] > 1:
                sid = f"{sid}-{used_ids[sid]}"
        sessions.append(Session(
            date=first.start.date().isoformat(),
            client=first.client,
            description=first.description,
            minutes=minutes,
            amount=f"{amount:.2f}",
            session_id=sid,
            sort_key=(norm(first.client), first.start, first.order),
        ))
    sessions.sort(key=lambda s: s.sort_key)
    return sessions
