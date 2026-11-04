"""Beyond-the-key robustness probe. Written before EGM finished, applied to all arms.

Not pass/fail on policy: each case records exit code, whether a Python
traceback leaked, and how many rows came out. "graceful" = no traceback
and exit code in {0, 2}.

    python3 -I _judge/robustness_probe.py arms/<arm>
"""
import subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
A = "Date,Description,Debit,Credit,Balance\n"
B = "Transaction Date,Posting Date,Details,Amount\n"
CASES = {
    "utf8_bom_header": "﻿" + A + "01/03/2026,Coffee,3.50,,0\n",
    "crlf_line_endings": (A + "01/03/2026,Coffee,3.50,,0\n").replace("\n", "\r\n"),
    "unclosed_quote": A + '01/03/2026,"Broken,3.50,,0\n02/03/2026,Next,4.00,,0\n03/03/2026,After,5.00,,0\n',
    "short_row": A + "01/03/2026,Coffee\n02/03/2026,Ok,1.00,,0\n",
    "empty_file": "",
    "header_only": B,
    "currency_symbol": B + "2026-03-01,2026-03-01,Thing,-£3.50\n2026-03-02,2026-03-02,Ok,-1.00\n",
    "invalid_calendar_date": A + "31/02/2026,Ghost,1.00,,0\n01/03/2026,Real,2.00,,0\n",
    "both_debit_and_credit": A + "01/03/2026,Odd,1.00,2.00,0\n02/03/2026,Ok,1.00,,0\n",
    "unicode_description": A + "01/03/2026,Café Ümlaut ☕,3.50,,0\n",
}

def run(name, text):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "in.csv").write_text(text, encoding="utf-8", newline="")
        (d / "rules.csv").write_text("pattern,category\ncoffee,Food\n")
        out = d / "out.csv"
        p = subprocess.run([sys.executable, "-m", "txmerge", "merge", "--account", f"acct={d/'in.csv'}",
                            "--rules", str(d / "rules.csv"), "--out", str(out)],
                           cwd=ROOT, capture_output=True, text=True, timeout=30)
        rows = max(len(out.read_text(encoding="utf-8").splitlines()) - 1, 0) if out.exists() else None
        tb = "Traceback" in p.stderr
        graceful = not tb and p.returncode in (0, 2)
        return p.returncode, tb, rows, graceful

score = 0
for name, text in CASES.items():
    rc, tb, rows, ok = run(name, text)
    score += ok
    print(f"{name:24} exit={rc} traceback={tb!s:5} rows={rows} {'graceful' if ok else 'CRASH'}")
print(f"graceful {score}/{len(CASES)}")
