"""Reference implementation of the stakeholder key. Judge-only."""
import argparse
import csv
import sys
from collections import Counter
from datetime import datetime, timedelta

A_HDR = ["Scanned At", "SKU", "Qty", "Unit"]
B_HDR = ["timestamp", "barcode", "count", "note"]
CASE_SIZE = 12
MOVE_WINDOW = timedelta(hours=2)


class BadHeader(Exception):
    pass


def parse_file(path):
    rows = []
    with open(path, newline="") as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader, [])]
        if header not in (A_HDR, B_HDR):
            raise BadHeader(f"{path}: unrecognised header {header}")
        for lineno, rec in enumerate(reader, start=2):
            try:
                if header == A_HDR:
                    ts = datetime.strptime(rec[0].strip(), "%d/%m/%Y %H:%M")
                    qty, unit = int(rec[2].strip()), rec[3].strip().lower()
                    if unit == "case":
                        qty *= CASE_SIZE
                    elif unit != "each":
                        raise ValueError(f"unknown unit {rec[3]!r}")
                else:
                    ts = datetime.fromisoformat(rec[0].strip())
                    if ts.tzinfo is not None:
                        raise ValueError("time zone offsets not supported")
                    ts = ts.replace(second=0, microsecond=0)
                    qty = int(rec[2].strip())
                sku = rec[1].strip()
                if not sku:
                    raise ValueError("blank SKU")
            except (ValueError, IndexError) as e:
                print(f"warning: {path}:{lineno}: skipped ({e})", file=sys.stderr)
                continue
            rows.append({"ts": ts, "qty": qty, "sku": sku})
    return rows


def norm(sku):
    return sku.strip().upper().lstrip("0") or "0"


def merge(locations, rules):
    inv, seq = [], 0
    by_location = {}
    for name, path in locations:
        by_location.setdefault(name, []).append(parse_file(path))
    for name, exports in by_location.items():
        kept = Counter()
        for rows in exports:
            seen = Counter()
            for r in rows:
                key = (r["ts"], r["qty"], norm(r["sku"]))
                seen[key] += 1
                if seen[key] > kept[key]:
                    kept[key] += 1
                    seq += 1
                    inv.append({**r, "nsku": norm(r["sku"]), "location": name, "seq": seq,
                                "move_id": "", "category": ""})

    scans = sorted(inv, key=lambda r: (r["ts"], r["location"], r["seq"]))
    used, mid = set(), 0
    for out in scans:
        if out["qty"] >= 0 or out["seq"] in used:
            continue
        best = None
        for inn in scans:
            if (inn["seq"] in used or inn["location"] == out["location"]
                    or inn["nsku"] != out["nsku"] or inn["qty"] != -out["qty"]):
                continue
            gap = abs(inn["ts"] - out["ts"])
            if gap <= MOVE_WINDOW and (best is None or gap < best[0]):
                best = (gap, inn)
        if best:
            mid += 1
            for r in (out, best[1]):
                used.add(r["seq"])
                r["move_id"] = f"M{mid:04d}"
                r["category"] = "Move"

    for r in inv:
        if not r["category"]:
            low = r["sku"].lower()
            r["category"] = next((c for p, c in rules if p.lower() in low), "Uncategorised")
    inv.sort(key=lambda r: (r["location"], r["nsku"], r["ts"], r["seq"]))
    return inv


def main(argv=None):
    ap = argparse.ArgumentParser(prog="stockmerge")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge")
    m.add_argument("--location", action="append", required=True)
    m.add_argument("--rules", required=True)
    m.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    locations = [tuple(a.split("=", 1)) for a in args.location]
    with open(args.rules, newline="") as f:
        rules = [(r["pattern"].strip(), r["category"]) for r in csv.DictReader(f) if r["pattern"].strip()]
    try:
        inv = merge(locations, rules)
    except BadHeader as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["location", "sku", "qty_each", "category", "move_id"])
        for r in inv:
            w.writerow([r["location"], r["sku"], r["qty"], r["category"], r["move_id"]])
    return 0
