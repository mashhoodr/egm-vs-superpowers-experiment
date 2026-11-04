"""Deterministic ids for joined sessions."""
from __future__ import annotations

import hashlib

from tsinvoice.model import Entry, Session, norm


def compute_id(entries: list[Entry]) -> str:
    lines = [f"{e.tracker}|{e.start.isoformat()}|{e.end.isoformat()}|"
             f"{norm(e.client)}|{norm(e.description)}" for e in entries]
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return "s-" + digest[:12]


def assign_ids(sessions: list[Session]) -> None:
    """Set ids in place; ``sessions`` must already be in output order."""
    used: dict[str, int] = {}
    for s in sessions:
        if len(s.entries) < 2:
            s.session_id = ""
            continue
        base = compute_id(s.entries)
        used[base] = used.get(base, 0) + 1
        s.session_id = base if used[base] == 1 else f"{base}-{used[base]}"
