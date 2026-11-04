"""CLI: python -m tsinvoice merge --tracker NAME=PATH ... --rates R --out O"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys

from .core import dedupe, join, price
from .parse import InputError, read_rates, read_tracker

HEADER = ["date", "client", "description", "minutes", "amount", "session_id"]


def _tracker_arg(value: str) -> tuple[str, str]:
    name, sep, path = value.partition("=")
    if not sep or not name.strip() or not path:
        raise argparse.ArgumentTypeError(f"expected NAME=PATH, got {value!r}")
    return name.strip(), path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tsinvoice")
    sub = p.add_subparsers(dest="command", required=True)
    m = sub.add_parser("merge", help="merge tracker exports into sessions")
    m.add_argument("--tracker", action="append", required=True,
                   type=_tracker_arg, metavar="NAME=PATH")
    m.add_argument("--rates", required=True)
    m.add_argument("--out", required=True)
    return p


def merge(trackers: list[tuple[str, str]], rates_path: str, out: str) -> None:
    rates = read_rates(rates_path)
    files = [read_tracker(name, path, i)
             for i, (name, path) in enumerate(trackers)]
    sessions = price(join(dedupe(files)), rates)

    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(HEADER)
    for s in sessions:
        w.writerow([s.date, s.client, s.description, s.minutes, s.amount,
                    s.session_id])
    tmp = out + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        fh.write(buf.getvalue())
    os.replace(tmp, out)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        merge(args.tracker, args.rates, args.out)
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
