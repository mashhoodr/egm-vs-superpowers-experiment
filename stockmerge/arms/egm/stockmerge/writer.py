"""Output rows and atomic CSV writing (R8.1, R9.1 to R9.3)."""

from __future__ import annotations

import csv
import os
import shutil
import tempfile

from stockmerge.model import MOVE_CATEGORY, OUTPUT_HEADER, Scan, StockmergeError, output_order
from stockmerge.rules import Rule, categorise


def build_rows(
    scans: list[Scan], move_ids: dict[tuple[int, int], str], rules: list[Rule]
) -> list[list[str]]:
    rows = []
    for s in sorted(scans, key=output_order):
        move_id = move_ids.get(s.ident)
        category = MOVE_CATEGORY if move_id else categorise(s.sku_norm, rules)
        rows.append([s.location, s.sku, str(s.qty_each), category, move_id or ""])
    return rows


def _current_umask() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return mask


def write_csv(out_path: str, rows: list[list[str]]) -> None:
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=os.path.dirname(os.path.abspath(out_path)),
            prefix=".stockmerge-",
            suffix=".tmp",
            delete=False,
        ) as f:
            tmp_name = f.name
            writer = csv.writer(f, lineterminator="\n")
            writer.writerow(OUTPUT_HEADER)
            writer.writerows(rows)
        if os.path.exists(out_path):
            shutil.copymode(out_path, tmp_name)
        else:
            os.chmod(tmp_name, 0o666 & ~_current_umask())
        os.replace(tmp_name, out_path)
    except (OSError, UnicodeError) as exc:
        if tmp_name is not None:
            try:
                os.remove(tmp_name)
            except OSError:
                pass
        raise StockmergeError(f"{out_path}: cannot write output: {exc}") from exc
