"""Render the merged inventory and write it to disk safely."""
from __future__ import annotations

import csv
import io
import os
import tempfile

from stockmerge.model import FatalError, Scan
from stockmerge.rules import Rule, categorise

HEADER = ["location", "sku", "qty_each", "category", "move_id"]


def output_order(scan: Scan) -> tuple:
    return (scan.location, scan.sku_key, scan.minute, scan.export_index, scan.line)


def render(scans: list[Scan], rules: list[Rule], moves: dict[tuple[int, int], str]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HEADER)
    for scan in sorted(scans, key=output_order):
        writer.writerow([scan.location, scan.sku_text, scan.qty_each,
                         categorise(scan.sku_text, rules), moves.get(scan.input_order, "")])
    return buffer.getvalue()


def write_atomic(path: str, text: str) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    try:
        fd, temp = tempfile.mkstemp(dir=directory, prefix=".stockmerge-", suffix=".tmp")
    except OSError as exc:
        raise FatalError(f"cannot write {path}: {exc.strerror}") from None
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        umask = os.umask(0)
        os.umask(umask)
        os.chmod(temp, 0o666 & ~umask)
        os.replace(temp, path)
    except (OSError, UnicodeError) as exc:
        if os.path.exists(temp):
            os.unlink(temp)
        reason = exc.strerror if isinstance(exc, OSError) else "text cannot be encoded as UTF-8"
        raise FatalError(f"cannot write {path}: {reason}") from None
