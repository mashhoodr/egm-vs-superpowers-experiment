"""Output CSV (Stage 9): atomic write via a temp file and os.replace."""

from __future__ import annotations

import csv
import os
import tempfile

from tsinvoice.model import FatalError, OutputRow

HEADER = ["date", "client", "description", "minutes", "amount", "session_id"]


def write_rows(out_path: str, rows: list[OutputRow]) -> None:
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(
            prefix=".tsinvoice-", dir=os.path.dirname(out_path) or "."
        )
        os.chmod(tmp, 0o644)
        with open(fd, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(HEADER)
            for r in rows:
                writer.writerow(
                    [r.date, r.client, r.description, r.minutes, r.amount, r.session_id]
                )
        os.replace(tmp, out_path)
    except OSError as e:
        if tmp is not None and os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass
        raise FatalError(f"{out_path}: cannot write: {e.strerror or e}") from e
