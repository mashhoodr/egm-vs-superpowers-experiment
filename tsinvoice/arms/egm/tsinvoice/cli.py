"""Argument parsing and orchestration (Stage 1, Stage 9)."""

from __future__ import annotations

import argparse
import sys

from tsinvoice import core, readers, writer
from tsinvoice.model import FatalError


def parse_tracker(value: str) -> tuple[str, str]:
    name, sep, path = value.partition("=")
    if not sep or not name or not path:
        raise argparse.ArgumentTypeError("expected NAME=PATH")
    return name, path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tsinvoice",
        description="Merge overlapping timesheet exports into invoice-ready sessions.",
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest="command", required=True)
    merge = sub.add_parser(
        "merge", help="merge exports into one sessions CSV", allow_abbrev=False
    )
    merge.add_argument(
        "--tracker",
        action="append",
        required=True,
        type=parse_tracker,
        metavar="NAME=PATH",
        help="one export of a tracker (repeatable)",
    )
    merge.add_argument("--rates", required=True, metavar="RATES.csv")
    merge.add_argument("--out", required=True, metavar="SESSIONS.csv")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rules = readers.read_rates(args.rates)
        entries = []
        bad_rows: list[str] = []
        for index, (name, path) in enumerate(args.tracker):
            got, warns = readers.read_export(path, name, index)
            entries.extend(got)
            bad_rows.extend(warns)
        rows, warnings = core.merge(entries, rules)
        writer.write_rows(args.out, rows)
    except FatalError as e:
        print(f"tsinvoice: error: {e}", file=sys.stderr)
        return 2
    for line in bad_rows + warnings:
        print(line, file=sys.stderr)
    return 0
