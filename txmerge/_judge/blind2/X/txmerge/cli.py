"""Argument parsing and orchestration."""

from __future__ import annotations

import argparse
import os
import sys

from .dedup import deduplicate
from .ledger import sort_rows, write_ledger
from .model import TxmergeError
from .readers import read_export
from .rules import categorise, load_rules
from .transfers import pair_transfers


def parse_account(value: str) -> tuple[str, str]:
    """D24: split on the first '='; both sides trimmed and non-empty."""
    name, sep, path = value.partition("=")
    name, path = name.strip(), path.strip()
    if not sep or not name or not path:
        raise argparse.ArgumentTypeError(f"--account must be NAME=PATH, got '{value}'")
    return name, path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="txmerge")
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("merge")
    m.add_argument("--account", action="append", required=True, type=parse_account)
    m.add_argument("--rules", required=True)
    m.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rules = load_rules(args.rules)

        rows = []
        skipped = 0
        for i, (name, path) in enumerate(args.account):
            parsed, n_skipped = read_export(path, name, i)
            rows.extend(parsed)
            skipped += n_skipped

        if os.path.exists(args.out):
            for x in [path for _, path in args.account] + [args.rules]:
                try:
                    same = os.path.samefile(args.out, x)
                except OSError as exc:
                    raise TxmergeError(f"cannot read {x}: {exc}") from exc
                if same:
                    raise TxmergeError(f"{args.out}: --out is also an input")

        kept = deduplicate(rows)
        ledger = sort_rows(kept)
        ids = pair_transfers(ledger)
        categories = [
            "Transfer" if ids[k] else categorise(row.description, rules)
            for k, row in enumerate(ledger)
        ]
        write_ledger(args.out, ledger, categories, ids)
    except TxmergeError as exc:
        print(f"txmerge: error: {exc}", file=sys.stderr)
        return 2

    read = len(rows) + skipped
    duplicates = len(rows) - len(kept)
    transfers = len({tid for tid in ids if tid})
    print(
        f"txmerge: {read} rows read, {skipped} skipped, {duplicates} duplicates removed, "
        f"{transfers} transfers linked, {len(ledger)} rows written",
        file=sys.stderr,
    )
    return 0
