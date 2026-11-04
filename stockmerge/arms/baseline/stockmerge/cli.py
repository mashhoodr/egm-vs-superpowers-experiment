"""Command-line entry point."""
from __future__ import annotations

import argparse
import sys

from stockmerge.core import InputError, merge, write_output


def _location(value: str) -> tuple[str, str]:
    name, sep, path = value.partition("=")
    if not sep or not name or not path:
        raise argparse.ArgumentTypeError(f"expected NAME=PATH, got {value!r}")
    return name, path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stockmerge")
    sub = p.add_subparsers(dest="command", required=True)
    m = sub.add_parser("merge", help="merge stock-take exports into one inventory")
    m.add_argument("--location", action="append", type=_location, required=True,
                   metavar="NAME=PATH", help="an export for a location (repeatable)")
    m.add_argument("--rules", required=True, help="CSV with header pattern,category")
    m.add_argument("--out", required=True, help="output inventory CSV")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        scans = merge(args.location, args.rules)
        write_output(scans, args.out)
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
