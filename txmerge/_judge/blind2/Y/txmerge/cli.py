"""Command-line entry point: python -m txmerge merge ..."""
import argparse
import sys

from txmerge.categorise import TRANSFER, categorise, load_rules
from txmerge.dedupe import dedupe
from txmerge.model import InputError, LedgerEntry
from txmerge.readers import read_export
from txmerge.transfers import order, pair_transfers
from txmerge.writer import write_ledger


def parse_account(value: str) -> tuple[str, str]:
    name, sep, path = value.partition("=")
    if not sep or not name.strip() or not path:
        raise argparse.ArgumentTypeError(f"expected NAME=PATH, got {value!r}")
    return name.strip(), path


def build_ledger(accounts: list[tuple[str, str]], rules_path: str, warn) -> list[LedgerEntry]:
    # Pipeline order is load-bearing: read -> dedupe -> sort -> pair -> categorise.
    rows = []
    for index, (name, path) in enumerate(accounts):
        rows.extend(read_export(name, path, index, warn))
    rules = load_rules(rules_path)
    ordered = order(dedupe(rows))
    ids = pair_transfers(ordered)
    return [LedgerEntry(t, TRANSFER if tid else categorise(t.description, rules), tid)
            for t, tid in zip(ordered, ids)]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="txmerge")
    sub = parser.add_subparsers(dest="command", required=True)
    merge = sub.add_parser("merge", help="merge bank exports into one ledger")
    merge.add_argument("--account", action="append", required=True, type=parse_account,
                       metavar="NAME=PATH")
    merge.add_argument("--rules", required=True)
    merge.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    def warn(message: str) -> None:
        print(message, file=sys.stderr)

    try:
        entries = build_ledger(args.account, args.rules, warn)
        write_ledger(args.out, entries)
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ArithmeticError as exc:
        print(f"error: amount cannot be written as a 2-decimal value ({exc.__class__.__name__})",
              file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: cannot write {args.out}: {exc.strerror or exc}", file=sys.stderr)
        return 2
    return 0
