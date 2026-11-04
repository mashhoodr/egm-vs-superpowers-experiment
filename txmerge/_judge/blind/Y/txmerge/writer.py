"""Write the merged ledger CSV."""
import csv
import io
import os
import tempfile
from decimal import ROUND_HALF_UP, Decimal

from txmerge.model import LedgerEntry

HEADER = ["date", "account", "description", "amount", "category", "transfer_id"]
_CENT = Decimal("0.01")


def format_amount(amount: Decimal) -> str:
    q = amount.quantize(_CENT, rounding=ROUND_HALF_UP)
    if q == 0:
        q = Decimal("0.00")
    return f"{q:f}"


def write_ledger(path: str, entries: list[LedgerEntry]) -> None:
    # Format everything first, then swap in atomically: never a partial file.
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    for e in entries:
        t = e.txn
        writer.writerow([t.date.isoformat(), t.account, t.description,
                         format_amount(t.amount), e.category, e.transfer_id])
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".txmerge-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            fh.write(buffer.getvalue())
        umask = os.umask(0)
        os.umask(umask)
        os.chmod(tmp, 0o666 & ~umask)  # mkstemp makes 0600; match a normal open()
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
