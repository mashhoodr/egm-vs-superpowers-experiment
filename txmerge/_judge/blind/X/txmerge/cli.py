"""Argument parsing and pipeline orchestration."""

from __future__ import annotations

import argparse
import sys

from txmerge.dedup import dedup
from txmerge.formats import read_export
from txmerge.ledger import check_not_input, write_ledger
from txmerge.model import EXIT_ERROR, EXIT_OK, UNCATEGORISED, Record, TxmergeError
from txmerge.rules import categorise, load_rules
from txmerge.transfers import pair_transfers


def account_arg(value: str) -> tuple[str, str]:
    name, sep, path = value.partition("=")
    if not sep or not name or not path:
        raise argparse.ArgumentTypeError(f"expected NAME=PATH, got '{value}'")
    return name, path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="txmerge", allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    merge = sub.add_parser(
        "merge",
        allow_abbrev=False,
        description=(
            "Merge bank exports. Accepted headers: Date,Description,Debit,Credit,Balance"
            " | Transaction Date,Posting Date,Details,Amount. Rules header: pattern,category."
        ),
    )
    merge.add_argument(
        "--account", type=account_arg, action="append", required=True, metavar="NAME=PATH"
    )
    merge.add_argument("--rules", required=True, metavar="RULES.csv")
    merge.add_argument("--out", required=True, metavar="LEDGER.csv")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    def warn(msg: str) -> None:
        print(f"txmerge: warning: {msg}", file=sys.stderr)

    skipped_total = 0
    records: list[Record] = []
    try:
        check_not_input(args.out, [path for _, path in args.account] + [args.rules])
        for index, (name, path) in enumerate(args.account):
            batch, skipped = read_export(index, name, path, warn)
            records.extend(batch)
            skipped_total += skipped
        rules = load_rules(args.rules, warn)
        parsed = len(records)
        kept = dedup(records)
        kept.sort(key=Record.sort_key)
        pairs = pair_transfers(kept)
        categorise(kept, rules)
        write_ledger(args.out, kept)
        written = len(kept)
        uncategorised = sum(1 for r in kept if r.category == UNCATEGORISED)
        print(
            f"txmerge: wrote {written} rows to {args.out} (parsed {parsed}, "
            f"skipped {skipped_total} malformed, removed {parsed - written} duplicates, "
            f"linked {pairs} transfer pairs, {uncategorised} uncategorised)",
            file=sys.stderr,
        )
        return EXIT_OK
    except TxmergeError as e:
        print(f"txmerge: error: {e}", file=sys.stderr)
        return EXIT_ERROR
