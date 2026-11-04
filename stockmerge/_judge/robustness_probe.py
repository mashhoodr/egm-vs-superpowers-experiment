"""Beyond-the-key robustness probe for stockmerge. Applied to all arms.

Not pass/fail on policy: each case records exit code, whether a Python
traceback leaked, and how many rows came out. "graceful" = no traceback
and exit code in {0, 2}. The out_is_input case also records whether the
input file was overwritten.

    python3 -I _judge/robustness_probe.py arms/<arm>
"""
import subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
A = "Scanned At,SKU,Qty,Unit\n"
B = "timestamp,barcode,count,note\n"
CASES = {
    "utf8_bom_header": "﻿" + A + "01/03/2026 09:00,COLA-330,3,each\n",
    "crlf_line_endings": (A + "01/03/2026 09:00,COLA-330,3,each\n").replace("\n", "\r\n"),
    "unclosed_quote": A + '01/03/2026 09:00,"COLA-330,3,each\n01/03/2026 09:01,NEXT,4,each\n01/03/2026 09:02,AFTER,5,each\n',
    "empty_file": "",
    "header_only": B,
    "invalid_calendar_date": A + "31/02/2026 09:00,GHOST,1,each\n01/03/2026 09:00,REAL,2,each\n",
    "unicode_sku": A + "01/03/2026 09:00,CAFÉ-Ü-☕,3,each\n",
    "b_timezone_offset": B + "2026-03-01T09:00:00+05:00,COLA-330,3,\n2026-03-01T09:01:00,OK,1,\n",
    "repeated_header_midfile": A + "01/03/2026 09:00,COLA-330,3,each\n" + A + "01/03/2026 09:01,OK,1,each\n",
    "out_is_input": A + "01/03/2026 09:00,COLA-330,3,each\n01/03/2026 09:01,OK,1,each\n",
}

def run(name, text):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        inp = d / "in.csv"
        inp.write_text(text, encoding="utf-8", newline="")
        before = inp.read_bytes()
        (d / "rules.csv").write_text("pattern,category\ncola,Drinks\n")
        out = inp if name == "out_is_input" else d / "out.csv"
        p = subprocess.run([sys.executable, "-m", "stockmerge", "merge", "--location", f"shop={inp}",
                            "--rules", str(d / "rules.csv"), "--out", str(out)],
                           cwd=ROOT, capture_output=True, text=True, timeout=30)
        rows = max(len(out.read_text(encoding="utf-8").splitlines()) - 1, 0) if out.exists() else None
        tb = "Traceback" in p.stderr
        graceful = not tb and p.returncode in (0, 2)
        extra = f" input_overwritten={inp.read_bytes() != before}" if name == "out_is_input" else ""
        return p.returncode, tb, rows, graceful, extra

score = 0
for name, text in CASES.items():
    rc, tb, rows, ok, extra = run(name, text)
    score += ok
    print(f"{name:24} exit={rc} traceback={tb!s:5} rows={rows} {'graceful' if ok else 'CRASH'}{extra}")
print(f"graceful {score}/{len(CASES)}")
