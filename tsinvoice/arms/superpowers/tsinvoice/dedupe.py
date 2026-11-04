"""Remove entries repeated across overlapping exports of the same tracker."""
from __future__ import annotations

from collections import defaultdict

from tsinvoice.model import Entry, norm


def _key(e: Entry):
    return (e.tracker, e.start, e.end, norm(e.client), norm(e.description))


def dedupe(entries: list[Entry]) -> list[Entry]:
    """Keep, per identity key, as many copies as the largest single export holds."""
    kept_count: dict = defaultdict(int)
    seen_in_file: dict = defaultdict(int)
    kept = []
    for e in sorted(entries, key=lambda x: x.order):
        key = _key(e)
        seen_in_file[key, e.arg_index] += 1
        if seen_in_file[key, e.arg_index] > kept_count[key]:
            kept_count[key] = seen_in_file[key, e.arg_index]
            kept.append(e)
    return kept
