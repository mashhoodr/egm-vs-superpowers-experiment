"""Command line layer (R1.x, R2.x, messages and exit codes)."""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys

from stockmerge.dedup import dedup
from stockmerge.model import StockmergeError, Warnings
from stockmerge.moves import link_moves
from stockmerge.readers import read_export
from stockmerge.rules import load_rules
from stockmerge.writer import build_rows, write_csv


def location_arg(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(f"expected NAME=PATH, got: {value}")
    name, path = value.split("=", 1)
    name, path = name.strip(), path.strip()
    if not name:
        raise argparse.ArgumentTypeError(f"empty location name in: {value}")
    if not path:
        raise argparse.ArgumentTypeError(f"empty path in: {value}")
    try:
        name.encode("utf-8")
    except UnicodeError:
        raise argparse.ArgumentTypeError("location name is not valid UTF-8") from None
    return name, path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stockmerge",
        description="Merge overlapping stock-take scans into one inventory.",
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest="command", required=True)
    merge = sub.add_parser(
        "merge", help="merge exports into one inventory CSV", allow_abbrev=False
    )
    merge.add_argument(
        "--location", action="append", type=location_arg, required=True,
        metavar="NAME=PATH", help="an export of location NAME (may repeat)",
    )
    merge.add_argument("--rules", required=True, help="rules CSV (pattern,category)")
    merge.add_argument("--out", required=True, help="output inventory CSV")
    return parser


def same_file(a: str, b: str) -> bool:
    try:
        if os.path.realpath(a) == os.path.realpath(b):
            return True
        if os.path.exists(a) and os.path.exists(b):
            return os.path.samefile(a, b)
    except (OSError, ValueError):
        return False
    return False


def fold_name(name: str) -> str:
    return re.sub(r" +", " ", name.lower())


def _warn_names(exports, warnings: Warnings) -> None:
    names: list[str] = []
    for _i, name, _p in exports:
        if name not in names:
            names.append(name)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if fold_name(a) == fold_name(b):
                warnings.add(None, None, f"location names '{a}' and '{b}' differ only by case or spaces")
    for i, (_ia, a, pa) in enumerate(exports):
        for _ib, b, pb in exports[i + 1:]:
            if a != b and same_file(pa, pb):
                warnings.add(None, None, f"{pa} is given for both '{a}' and '{b}'")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    exports = [(i, name, path) for i, (name, path) in enumerate(args.location)]
    warnings = Warnings()
    current_path = "stockmerge"
    try:
        _warn_names(exports, warnings)
        for p in [path for _i, _n, path in exports] + [args.rules]:
            if same_file(args.out, p):
                raise StockmergeError(f"--out {args.out} is also an input file")
        current_path = args.rules
        rules = load_rules(args.rules, warnings)
        scans = []
        read = skipped = 0
        for i, name, path in exports:
            current_path = path
            got, r, s = read_export(i, name, path, warnings)
            scans.extend(got)
            read += r
            skipped += s
        current_path = "stockmerge"
        kept, removed = dedup(scans)
        move_ids = link_moves(kept)
        rows = build_rows(kept, move_ids, rules)
        current_path = args.out
        write_csv(args.out, rows)
    except StockmergeError as exc:
        sys.stderr.write(f"stockmerge: error: {exc}\n")
        return 2
    except (OSError, UnicodeError, csv.Error) as exc:
        where = getattr(exc, "filename", None) or current_path
        detail = exc.strerror if isinstance(exc, OSError) and exc.strerror else str(exc)
        sys.stderr.write(f"stockmerge: error: {where}: {detail}\n")
        return 2
    sys.stderr.write(
        f"stockmerge: read {read} rows, removed {removed} duplicates, "
        f"skipped {skipped} rows, linked {len(move_ids) // 2} moves, "
        f"wrote {len(rows)} rows\n"
    )
    return 0
