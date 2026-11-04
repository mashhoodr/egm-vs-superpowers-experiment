"""Command-line entry point: python -m tsinvoice merge ..."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from decimal import Decimal

from tsinvoice.dedupe import dedupe
from tsinvoice.join import join
from tsinvoice.model import FatalError
from tsinvoice.output import render_csv, session_row, sort_sessions
from tsinvoice.parse import read_tracker
from tsinvoice.rates import find_rate, load_rates, price
from tsinvoice.session_id import assign_ids


def _warn(message: str) -> None:
    print(message, file=sys.stderr)


def parse_tracker_arg(text: str) -> tuple[str, str]:
    name, sep, path = text.partition("=")
    if not sep or not name.strip() or not path:
        raise FatalError(f"--tracker must be NAME=PATH, got {text!r}")
    return name.strip(), path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tsinvoice")
    sub = parser.add_subparsers(dest="command", required=True)
    merge = sub.add_parser("merge", help="merge tracker exports into priced sessions")
    merge.add_argument("--tracker", action="append", required=True, metavar="NAME=PATH")
    merge.add_argument("--rates", required=True)
    merge.add_argument("--out", required=True)
    return parser


def _merge(trackers: list[str], rates_path: str) -> str:
    specs = [parse_tracker_arg(t) for t in trackers]
    rates = load_rates(rates_path, _warn)
    entries = []
    for arg_index, (name, path) in enumerate(specs):
        entries.extend(read_tracker(path, name, arg_index, _warn))
    sessions = sort_sessions(join(dedupe(entries)))
    assign_ids(sessions)
    rows = []
    for s in sessions:
        rate = find_rate(s.client, s.description, rates)
        if rate is None:
            _warn(f"warning: no rate for client '{s.client}' description '{s.description}'")
            amount = price(s.minutes, Decimal(0))
        else:
            amount = price(s.minutes, rate)
        rows.append(session_row(s, amount))
    return render_csv(rows)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        text = _merge(args.tracker, args.rates)
    except FatalError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", newline="", delete=False,
                dir=os.path.dirname(os.path.abspath(args.out)),
                prefix=".tsinvoice-", suffix=".tmp") as fh:
            tmp = fh.name
            fh.write(text)
        os.replace(tmp, args.out)
    except OSError as exc:
        if tmp is not None:
            try:
                os.remove(tmp)
            except OSError:
                pass
        print(f"error: cannot write {args.out}: {exc}", file=sys.stderr)
        return 2
    return 0
