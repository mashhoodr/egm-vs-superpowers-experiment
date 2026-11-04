"""Reference implementation of the stakeholder key. Judge-only."""
import argparse
import csv
import sys
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

A_HDR = ["Date", "Description", "Debit", "Credit", "Balance"]
B_HDR = ["Transaction Date", "Posting Date", "Details", "Amount"]


class BadHeader(Exception):
    pass


def money(s):
    return Decimal(s.replace(",", "").strip())


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
                    d = datetime.strptime(rec[0].strip(), "%d/%m/%Y").date()
                    debit, credit = rec[2].strip(), rec[3].strip()
                    if debit and not credit:
                        amt = -money(debit)
                    elif credit and not debit:
                        amt = money(credit)
                    else:
                        raise ValueError("need exactly one of debit/credit")
                    desc = rec[1]
                else:
                    d = date.fromisoformat(rec[0].strip())
                    amt, desc = money(rec[3]), rec[2]
            except (ValueError, IndexError, InvalidOperation) as e:
                print(f"warning: {path}:{lineno}: skipped ({e})", file=sys.stderr)
                continue
            rows.append({"date": d, "amount": amt, "description": desc.strip()})
    return rows


def norm(desc):
    return " ".join(desc.split()).lower()


def merge(accounts, rules):
    ledger, seq = [], 0
    by_account = {}
    for name, path in accounts:
        by_account.setdefault(name, []).append(parse_file(path))
    for name, exports in by_account.items():
        kept = Counter()
        for rows in exports:
            seen = Counter()
            for r in rows:
                key = (r["date"], r["amount"], norm(r["description"]))
                seen[key] += 1
                if seen[key] > kept[key]:
                    kept[key] += 1
                    seq += 1
                    ledger.append({**r, "account": name, "seq": seq, "transfer_id": "", "category": ""})
    ledger.sort(key=lambda r: (r["date"], r["account"], r["seq"]))

    used, tid = set(), 0
    for i, out in enumerate(ledger):
        if out["amount"] >= 0 or i in used:
            continue
        best = None
        for j, inn in enumerate(ledger):
            if (j in used or inn["account"] == out["account"] or inn["amount"] != -out["amount"]):
                continue
            gap = abs((inn["date"] - out["date"]).days)
            if gap <= 3 and (best is None or gap < best[0]):
                best = (gap, j)
        if best:
            tid += 1
            used.update({i, best[1]})
            for k in (i, best[1]):
                ledger[k]["transfer_id"] = f"T{tid:04d}"
                ledger[k]["category"] = "Transfer"

    for r in ledger:
        if not r["category"]:
            low = r["description"].lower()
            r["category"] = next((c for p, c in rules if p.lower() in low), "Uncategorised")
    return ledger


def main(argv=None):
    ap = argparse.ArgumentParser(prog="txmerge")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge")
    m.add_argument("--account", action="append", required=True)
    m.add_argument("--rules", required=True)
    m.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    accounts = [tuple(a.split("=", 1)) for a in args.account]
    with open(args.rules, newline="") as f:
        rules = [(r["pattern"], r["category"]) for r in csv.DictReader(f) if r["pattern"]]
    try:
        ledger = merge(accounts, rules)
    except BadHeader as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["date", "account", "description", "amount", "category", "transfer_id"])
        for r in ledger:
            w.writerow([r["date"].isoformat(), r["account"], r["description"],
                        f"{r['amount']:.2f}", r["category"], r["transfer_id"]])
    return 0
