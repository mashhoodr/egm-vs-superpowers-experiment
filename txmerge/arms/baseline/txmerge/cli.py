"""Command-line entry point: python -m txmerge merge ..."""
from __future__ import annotations

import argparse
import csv
import os
import sys
import tempfile

from .core import OUTPUT_HEADER, InputError, build_ledger, ledger_rows, read_export, read_rules

EXIT_OK = 0
EXIT_INPUT_ERROR = 2


def _account_arg(value: str) -> tuple[str, str]:
    name, sep, path = value.partition("=")
    if not sep or not name.strip() or not path.strip():
        raise argparse.ArgumentTypeError(f"expected NAME=PATH, got {value!r}")
    return name.strip(), path.strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="txmerge")
    sub = parser.add_subparsers(dest="command", required=True)
    merge = sub.add_parser("merge", help="merge exports into one ledger")
    merge.add_argument("--account", action="append", required=True, type=_account_arg,
                       metavar="NAME=PATH", help="an export for account NAME (repeatable)")
    merge.add_argument("--rules", required=True, help="CSV with header pattern,category")
    merge.add_argument("--out", required=True, help="output ledger CSV")
    return parser


def write_ledger(path: str, rows: list[list[str]]) -> None:
    """Write atomically so a failed run never leaves a partial ledger."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".txmerge-", suffix=".csv", dir=directory)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow(OUTPUT_HEADER)
            writer.writerows(rows)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rules = read_rules(args.rules)
        exports = [read_export(path, name, i) for i, (name, path) in enumerate(args.account)]
        ledger = build_ledger(exports, rules)
        write_ledger(args.out, ledger_rows(ledger))
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    except OSError as exc:
        print(f"error: cannot write {args.out}: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    return EXIT_OK
