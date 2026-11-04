"""Beyond-the-key robustness probe. Applied to all arms.

Not pass/fail on policy: each case records exit code, whether a Python
traceback leaked, and how many rows came out. "graceful" = no traceback
and exit code in {0, 2}. The out_is_input case also records whether the
input file was overwritten.

    python3 -I _judge/robustness_probe.py arms/<arm>
"""
import subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
A = "Client,Description,Start,End\n"
B = "client,task,start_iso,duration_minutes\n"
RATES = "pattern,hourly_rate\nacme,60.00\n"
OK = "Acme,Design,01/03/2026 09:00,01/03/2026 10:00\n"
# name: (input text, rates text, --out points at the input file)
CASES = {
    "utf8_bom_header": ("﻿" + A + OK, RATES, False),
    "crlf_line_endings": ((A + OK).replace("\n", "\r\n"), RATES, False),
    "unclosed_quote": (A + 'Acme,"Broken,01/03/2026 09:00,01/03/2026 10:00\n'
                       "Acme,Next,02/03/2026 09:00,02/03/2026 10:00\n"
                       "Acme,After,03/03/2026 09:00,03/03/2026 10:00\n", RATES, False),
    "empty_file": ("", RATES, False),
    "header_only": (B, RATES, False),
    "invalid_calendar_date": (A + "Acme,Ghost,31/02/2026 09:00,31/02/2026 10:00\n" + OK, RATES, False),
    "unicode_description": (A + "Café Ümlaut,Design ☕ review,01/03/2026 09:00,01/03/2026 10:00\n", RATES, False),
    "b_fractional_duration": (B + "Acme,Design,2026-03-01T09:00:00,30.5\nAcme,Ok,2026-03-02T09:00:00,30\n", RATES, False),
    "rate_with_currency_symbol": (A + OK, "pattern,hourly_rate\nacme,$60.00\n", False),
    "out_is_input": (A + OK, RATES, True),
}

def run(name, text, rates, out_is_input):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        inp = d / "in.csv"
        inp.write_text(text, encoding="utf-8", newline="")
        (d / "rates.csv").write_text(rates, encoding="utf-8")
        out = inp if out_is_input else d / "out.csv"
        p = subprocess.run([sys.executable, "-m", "tsinvoice", "merge", "--tracker", f"t={inp}",
                            "--rates", str(d / "rates.csv"), "--out", str(out)],
                           cwd=ROOT, capture_output=True, text=True, timeout=30)
        rows = max(len(out.read_text(encoding="utf-8").splitlines()) - 1, 0) if out.exists() else None
        clobbered = out_is_input and inp.read_text(encoding="utf-8") != text
        tb = "Traceback" in p.stderr
        graceful = not tb and p.returncode in (0, 2)
        return p.returncode, tb, rows, graceful, clobbered

score = 0
for name, (text, rates, same) in CASES.items():
    rc, tb, rows, ok, clob = run(name, text, rates, same)
    score += ok
    extra = f" input_overwritten={clob}" if same else ""
    print(f"{name:26} exit={rc} traceback={tb!s:5} rows={rows} {'graceful' if ok else 'CRASH'}{extra}")
print(f"graceful {score}/{len(CASES)}")
