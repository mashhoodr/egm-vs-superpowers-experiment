import csv
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
A = "Client,Description,Start,End\n"
B = "client,task,start_iso,duration_minutes\n"
RATES = "pattern,hourly_rate\nacme,60\nbeta,90\n"


def run(tmp_path, trackers, rates=RATES):
    args = [sys.executable, "-m", "tsinvoice", "merge"]
    for i, (name, body) in enumerate(trackers):
        p = tmp_path / f"t{i}.csv"
        p.write_text(body)
        args += ["--tracker", f"{name}={p}"]
    rp = tmp_path / "rates.csv"
    if rates is not None:
        rp.write_text(rates)
    out = tmp_path / "out.csv"
    proc = subprocess.run(args + ["--rates", str(rp), "--out", str(out)],
                          cwd=ROOT, capture_output=True, text=True)
    rows = None
    if out.exists():
        with open(out, newline="") as fh:
            rows = list(csv.DictReader(fh))
    return proc, rows, out


def test_header_and_single_entry(tmp_path):
    proc, rows, out = run(tmp_path, [("desk", A + "Acme,Build,01/03/2026 09:00,01/03/2026 10:00\n")])
    assert proc.returncode == 0, proc.stderr
    assert out.read_text().splitlines()[0] == "date,client,description,minutes,amount,session_id"
    assert rows == [{"date": "2026-03-01", "client": "Acme", "description": "Build",
                     "minutes": "60", "amount": "60.00", "session_id": ""}]


def test_overlapping_exports_dedupe(tmp_path):
    row = "Acme,Build,01/03/2026 09:00,01/03/2026 10:00\n"
    proc, rows, _ = run(tmp_path, [("desk", A + row), ("desk", A + "acme , build ,01/03/2026 09:00,01/03/2026 10:00\n")])
    assert len(rows) == 1


def test_same_file_repeats_kept(tmp_path):
    row = "Acme,Standup,01/03/2026 09:00,01/03/2026 09:30\n"
    proc, rows, _ = run(tmp_path, [("desk", A + row + row), ("desk", A + row)])
    assert len(rows) == 2


def test_different_trackers_never_dedupe(tmp_path):
    proc, rows, _ = run(tmp_path, [
        ("desk", A + "Acme,Build,01/03/2026 09:00,01/03/2026 10:00\n"),
        ("phone", B + "Acme,Build,2026-03-01T09:00:00,60\n")])
    assert len(rows) == 2
    assert all(r["session_id"] == "" for r in rows)


def test_edited_entry_keeps_both(tmp_path):
    proc, rows, _ = run(tmp_path, [
        ("desk", A + "Acme,Build,01/03/2026 09:00,01/03/2026 10:00\n"),
        ("desk", A + "Acme,Build,01/03/2026 09:00,01/03/2026 10:30\n")])
    assert sorted(r["minutes"] for r in rows) == ["60", "90"]


def test_continuation_across_trackers_and_rounding(tmp_path):
    proc, rows, _ = run(tmp_path, [
        ("desk", A + "Acme,Fix bug,01/03/2026 09:00,01/03/2026 09:07\n"),
        ("phone", B + "acme,fix  bug,2026-03-01T09:07:00+05:00,7\n")])
    assert len(rows) == 1
    r = rows[0]
    assert r["minutes"] == "18" and r["amount"] == "18.00"
    assert r["description"] == "Fix bug" and r["session_id"]


def test_chain_with_gaps_up_to_two_minutes(tmp_path):
    proc, rows, _ = run(tmp_path, [
        ("desk", A + "Acme,X,01/03/2026 09:00,01/03/2026 10:00\n"
                     "Acme,X,01/03/2026 10:31,01/03/2026 11:00\n"),
        ("phone", B + "Acme,X,2026-03-01T10:01,29\n")])
    assert len(rows) == 1
    assert rows[0]["minutes"] == "120"  # 60+29+29 = 118 -> 120


def test_gap_of_three_or_different_description_does_not_join(tmp_path):
    proc, rows, _ = run(tmp_path, [("desk", A +
        "Acme,X,01/03/2026 09:00,01/03/2026 10:00\n"
        "Acme,X,01/03/2026 10:03,01/03/2026 10:30\n"
        "Acme,Y,01/03/2026 10:30,01/03/2026 11:00\n")])
    assert len(rows) == 3


def test_overlap_not_joined(tmp_path):
    proc, rows, _ = run(tmp_path, [("desk", A +
        "Acme,X,01/03/2026 10:00,01/03/2026 11:00\n"
        "Acme,X,01/03/2026 10:30,01/03/2026 11:30\n")])
    assert len(rows) == 2


def test_successor_tie_smallest_gap_then_input_order(tmp_path):
    proc, rows, _ = run(tmp_path, [
        ("desk", A + "Acme,X,01/03/2026 09:00,01/03/2026 10:00\n"
                     "Acme,X,01/03/2026 10:01,01/03/2026 10:10\n"),
        ("phone", B + "Acme,X,2026-03-01T10:00,20\n")])
    by_min = sorted((r["minutes"], r["session_id"] != "") for r in rows)
    # 09-10 joins the 10:00 phone entry (gap 0) -> 80 billed 84; 10:01 entry stands alone -> 12
    assert by_min == [("12", False), ("84", True)]


def test_rates_first_match_case_insensitive_and_description(tmp_path):
    rates = "pattern,hourly_rate\nURGENT,120\nacme,60\n"
    proc, rows, _ = run(tmp_path, [("desk", A +
        "Acme,urgent fix,01/03/2026 09:00,01/03/2026 10:00\n"
        "Gamma,ACME port,01/03/2026 12:00,01/03/2026 13:00\n")], rates)
    amounts = {r["client"]: r["amount"] for r in rows}
    assert amounts == {"Acme": "120.00", "Gamma": "60.00"}


def test_unmatched_rate_zero_with_warning(tmp_path):
    proc, rows, _ = run(tmp_path, [("desk", A + "Zeta,Work,01/03/2026 09:00,01/03/2026 09:30\n")])
    assert proc.returncode == 0
    assert rows[0]["amount"] == "0.00"
    assert "Zeta" in proc.stderr and "Work" in proc.stderr


def test_amount_half_up(tmp_path):
    # 6 minutes at 12.25/h = 1.225 -> 1.23 (half-up)
    proc, rows, _ = run(tmp_path, [("desk", A + "Acme,X,01/03/2026 09:00,01/03/2026 09:06\n")],
                        "pattern,hourly_rate\nacme,12.25\n")
    assert rows[0]["amount"] == "1.23"


def test_bad_rows_skipped_with_warning(tmp_path):
    proc, rows, _ = run(tmp_path, [
        ("desk", A + "Acme,X,01/03/2026 09:00,\n"
                     "Acme,X,01/03/2026 09:00,01/03/2026 08:00\n"
                     "Acme,X,garbage,01/03/2026 08:00\n"
                     "Acme,X,01/03/2026 12:00,01/03/2026 12:30\n"),
        ("phone", B + "Acme,X,2026-03-01T14:00,30.5\nAcme,X,2026-03-01T15:00,0\n"
                      "Acme,X,2026-03-01T16:00,30.0\n")])
    assert proc.returncode == 0
    assert len(rows) == 2  # 12:00 desktop + "30.0" phone entry
    assert "t0.csv:2" in proc.stderr and "t1.csv:2" in proc.stderr


def test_unknown_header_exit_2_no_output(tmp_path):
    proc, rows, out = run(tmp_path, [("desk", "foo,bar\n1,2\n")])
    assert proc.returncode == 2 and not out.exists()


def test_missing_rates_exit_2(tmp_path):
    proc, rows, out = run(tmp_path, [("desk", A)], rates=None)
    assert proc.returncode == 2 and not out.exists()


def test_sort_by_client_then_start(tmp_path):
    proc, rows, _ = run(tmp_path, [("desk", A +
        "beta,X,02/03/2026 08:00,02/03/2026 09:00\n"
        "Acme,X,03/03/2026 09:00,03/03/2026 10:00\n"
        "acme,Y,01/03/2026 09:00,01/03/2026 10:00\n")])
    assert [(r["client"], r["date"]) for r in rows] == [
        ("acme", "2026-03-01"), ("Acme", "2026-03-03"), ("beta", "2026-03-02")]


def test_deterministic_output(tmp_path):
    trackers = [("desk", A + "Acme,X,01/03/2026 09:00,01/03/2026 09:30\n"),
                ("phone", B + "Acme,X,2026-03-01T09:31,10\n")]
    _, _, out = run(tmp_path, trackers)
    first = out.read_bytes()
    _, _, out = run(tmp_path, trackers)
    assert out.read_bytes() == first


def test_iso_seconds_truncated_and_date_is_start_date(tmp_path):
    proc, rows, _ = run(tmp_path, [("phone", B + "Acme,Night,2026-03-01T23:30:45Z,60\n")])
    assert rows[0]["date"] == "2026-03-01" and rows[0]["minutes"] == "60"
