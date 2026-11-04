"""Reference implementation of the stakeholder key. Judge-only."""
import argparse
import csv
import sys
from collections import Counter
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

A_HDR = ["Client", "Description", "Start", "End"]
B_HDR = ["client", "task", "start_iso", "duration_minutes"]
A_FMT = "%d/%m/%Y %H:%M"


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
                client, desc = rec[0], rec[1]
                if header == A_HDR:
                    start = datetime.strptime(rec[2].strip(), A_FMT)
                    end = datetime.strptime(rec[3].strip(), A_FMT)
                    if end <= start:
                        raise ValueError("end not after start")
                else:
                    start = datetime.fromisoformat(rec[2].strip()).replace(tzinfo=None)
                    dur = int(rec[3].strip())
                    if dur <= 0:
                        raise ValueError("duration must be above zero")
                    end = start + timedelta(minutes=dur)
            except (ValueError, IndexError) as e:
                print(f"warning: {path}:{lineno}: skipped ({e})", file=sys.stderr)
                continue
            rows.append({"start": start, "end": end, "client": client.strip(),
                         "description": desc.strip(), "line": lineno})
    return rows


def norm(s):
    return " ".join(s.split()).lower()


def ident(r):
    return (norm(r["client"]), norm(r["description"]))


def merge(trackers, rates):
    pieces, seq = [], 0
    by_tracker = {}
    for name, path in trackers:
        by_tracker.setdefault(name, []).append(parse_file(path))
    for name, exports in by_tracker.items():
        kept = Counter()
        for rows in exports:
            seen = Counter()
            for r in rows:
                key = (r["start"], r["end"], *ident(r))
                seen[key] += 1
                if seen[key] > kept[key]:
                    kept[key] += 1
                    seq += 1
                    pieces.append({**r, "seq": seq})
    pieces.sort(key=lambda p: (p["start"], p["seq"]))

    nxt, has_prev = {}, set()
    for i, p in enumerate(pieces):
        best = None
        for j, q in enumerate(pieces):
            if j == i or j in has_prev or ident(q) != ident(p):
                continue
            gap = (q["start"] - p["end"]).total_seconds()
            if 0 <= gap <= 120 and (best is None or gap < best[0]):
                best = (gap, j)
        if best:
            nxt[i] = best[1]
            has_prev.add(best[1])

    sessions, sid = [], 0
    for i, p in enumerate(pieces):
        if i in has_prev:
            continue
        chain = [i]
        while chain[-1] in nxt:
            chain.append(nxt[chain[-1]])
        total = sum((pieces[k]["end"] - pieces[k]["start"]).total_seconds() for k in chain) / 60
        minutes = -(-int(total) // 6) * 6
        session_id = ""
        if len(chain) > 1:
            sid += 1
            session_id = f"S{sid:04d}"
        sessions.append({**p, "minutes": minutes, "session_id": session_id})

    for s in sessions:
        lc, ld = s["client"].lower(), s["description"].lower()
        rate = next((r for pat, r in rates if pat.lower() in lc or pat.lower() in ld), None)
        if rate is None:
            print(f"warning: no rate for {s['client']!r} / {s['description']!r}", file=sys.stderr)
            rate = Decimal(0)
        s["amount"] = (Decimal(s["minutes"]) * rate / 60).quantize(Decimal("0.01"), ROUND_HALF_UP)
    sessions.sort(key=lambda s: (norm(s["client"]), s["start"], s["seq"]))
    return sessions


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tsinvoice")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge")
    m.add_argument("--tracker", action="append", required=True)
    m.add_argument("--rates", required=True)
    m.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    trackers = [tuple(t.split("=", 1)) for t in args.tracker]
    with open(args.rates, newline="") as f:
        rates = [(r["pattern"], Decimal(r["hourly_rate"].strip()))
                 for r in csv.DictReader(f) if r["pattern"]]
    try:
        sessions = merge(trackers, rates)
    except BadHeader as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["date", "client", "description", "minutes", "amount", "session_id"])
        for s in sessions:
            w.writerow([s["start"].date().isoformat(), s["client"], s["description"],
                        s["minutes"], f"{s['amount']:.2f}", s["session_id"]])
    return 0
