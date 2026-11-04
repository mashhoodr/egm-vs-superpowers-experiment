"""Command-line entry point: python -m stockmerge merge ..."""
from __future__ import annotations

import argparse
import sys
from typing import Callable

from stockmerge.dedupe import dedupe
from stockmerge.model import FatalError
from stockmerge.moves import link_moves
from stockmerge.readers import read_export
from stockmerge.rules import load_rules
from stockmerge.writer import render, write_atomic


def parse_location(value: str) -> tuple[str, str]:
    name, sep, path = value.partition("=")
    name = name.strip()
    if not sep or not name or not path:
        raise argparse.ArgumentTypeError(f"expected NAME=PATH, got {value!r}")
    return name, path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stockmerge")
    commands = parser.add_subparsers(dest="command", required=True)
    merge = commands.add_parser("merge", help="merge scanner exports into one inventory")
    merge.add_argument("--location", action="append", required=True, type=parse_location,
                       metavar="NAME=PATH", help="an export of location NAME (repeatable)")
    merge.add_argument("--rules", required=True, help="CSV with header pattern,category")
    merge.add_argument("--out", required=True, help="output inventory CSV")
    return parser


def run_merge(locations: list[tuple[str, str]], rules_path: str, out_path: str,
              warn: Callable[[str], None]) -> None:
    rules = load_rules(rules_path, warn)
    scans = []
    for index, (name, path) in enumerate(locations):
        scans.extend(read_export(path, name, index, warn))
    kept = dedupe(scans)
    write_atomic(out_path, render(kept, rules, link_moves(kept)))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run_merge(args.location, args.rules, args.out,
                  lambda message: print(message, file=sys.stderr))
    except FatalError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
