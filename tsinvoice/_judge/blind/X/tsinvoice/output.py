"""Order sessions and render the output CSV."""
from __future__ import annotations

import csv
import io
from decimal import Decimal

from tsinvoice.model import Session, norm

OUTPUT_HEADER = ["date", "client", "description", "minutes", "amount", "session_id"]


def sort_sessions(sessions: list[Session]) -> list[Session]:
    return sorted(sessions, key=lambda s: (norm(s.client), s.start,
                                           s.first.arg_index, s.first.line))


def session_row(session: Session, amount: Decimal) -> list[str]:
    return [session.date.isoformat(), session.client, session.description,
            str(session.minutes), f"{amount:.2f}", session.session_id]


def render_csv(rows: list[list[str]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(OUTPUT_HEADER)
    writer.writerows(rows)
    return buf.getvalue()
