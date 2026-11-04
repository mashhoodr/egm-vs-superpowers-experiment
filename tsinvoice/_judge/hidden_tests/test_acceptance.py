"""Hidden acceptance tests. Run against an arm with:

    TSINVOICE_ROOT=/path/to/arm/repo pytest -q _judge/hidden_tests

Each test is tagged with the stakeholder-key policy it checks (K1..K12).
Tests check policy outcomes, not incidental choices (e.g. session_id format).
"""
import csv
import io
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(os.environ.get("TSINVOICE_ROOT", Path(__file__).parent.parent / "reference"))

A_HDR = "Client,Description,Start,End\n"
B_HDR = "client,task,start_iso,duration_minutes\n"
COLS = ["date", "client", "description", "minutes", "amount", "session_id"]


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


def rates(tmp_path, rows=(("acme", "60.00"),)):
    return write(tmp_path, "rates.csv", "pattern,hourly_rate\n" + "".join(f"{p},{r}\n" for p, r in rows))


def run(tmp_path, trackers, rates_path, out_name="sessions.csv"):
    out = tmp_path / out_name
    cmd = [sys.executable, "-m", "tsinvoice", "merge"]
    for name, path in trackers:
        cmd += ["--tracker", f"{name}={path}"]
    cmd += ["--rates", rates_path, "--out", str(out)]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
    return proc, out


def sessions(out):
    text = out.read_text()
    reader = csv.DictReader(io.StringIO(text))
    assert reader.fieldnames == COLS, f"bad header: {reader.fieldnames}"
    return list(reader)


def merge_ok(tmp_path, trackers, rates_path):
    proc, out = run(tmp_path, trackers, rates_path)
    assert proc.returncode == 0, proc.stderr
    return sessions(out)


def a_row(client, desc, day, start, end):
    return f"{client},{desc},{day}/03/2026 {start},{day}/03/2026 {end}\n"


# --- contract -----------------------------------------------------------

def test_contract_header_and_formatting(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + a_row("Acme", "Design", "05", "09:00", "10:00"))
    rows = merge_ok(tmp_path, [("desk", a)], rates(tmp_path))
    assert rows == [{"date": "2026-03-05", "client": "Acme", "description": "Design",
                     "minutes": "60", "amount": "60.00", "session_id": ""}]


# --- K1 / K2 / K3 dedup ------------------------------------------------

def test_K1_overlap_dedup_with_normalised_client_and_description(tmp_path):
    e1 = write(tmp_path, "e1.csv", A_HDR + a_row("Acme  Corp", "Logo Design", "01", "09:00", "10:00")
               + a_row("Acme Corp", "Review", "02", "09:00", "09:30"))
    e2 = write(tmp_path, "e2.csv", A_HDR + a_row("acme corp ", "logo   design", "01", "09:00", "10:00")
               + a_row("Acme Corp", "Call", "03", "09:00", "09:30"))
    rows = merge_ok(tmp_path, [("desk", e1), ("desk", e2)], rates(tmp_path))
    assert [(r["date"], r["minutes"]) for r in rows] == [
        ("2026-03-01", "60"), ("2026-03-02", "30"), ("2026-03-03", "30")]


def test_K2_identical_entries_within_one_export_are_kept(tmp_path):
    e1 = write(tmp_path, "e1.csv", A_HDR + a_row("Acme", "Standup", "01", "09:00", "09:30") * 2)
    rows = merge_ok(tmp_path, [("desk", e1)], rates(tmp_path))
    assert len(rows) == 2


def test_K2_cross_export_count_is_max_not_sum(tmp_path):
    entry = a_row("Acme", "Standup", "01", "09:00", "09:30")
    e1 = write(tmp_path, "e1.csv", A_HDR + entry * 2)
    e2 = write(tmp_path, "e2.csv", A_HDR + entry * 3)
    rows = merge_ok(tmp_path, [("desk", e1), ("desk", e2)], rates(tmp_path))
    assert len(rows) == 3


def test_K3_different_trackers_never_dedup(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + a_row("Acme", "Design", "01", "09:00", "09:30"))
    b = write(tmp_path, "b.csv", B_HDR + "Acme,Design,2026-03-01T09:00:00,30\n")
    rows = merge_ok(tmp_path, [("desk", a), ("phone", b)], rates(tmp_path))
    assert len(rows) == 2


# --- K4 / K5 / K6 parsing ----------------------------------------------

def test_K4_format_b_offset_dropped_not_converted(tmp_path):
    b = write(tmp_path, "b.csv", B_HDR + "Acme,Late call,2026-03-01T23:00:00-05:00,30\n")
    rows = merge_ok(tmp_path, [("phone", b)], rates(tmp_path))
    assert [(r["date"], r["minutes"]) for r in rows] == [("2026-03-01", "30")]


def test_K5_bad_rows_skipped_with_warning(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + a_row("Acme", "Good", "01", "09:00", "09:30")
              + "Acme,Blank end,02/03/2026 09:00,\n"
              + a_row("Acme", "Backwards", "03", "10:00", "09:00")
              + "Acme,Bad date,not-a-date,03/03/2026 11:00\n")
    proc, out = run(tmp_path, [("desk", a)], rates(tmp_path))
    assert proc.returncode == 0, proc.stderr
    rows = sessions(out)
    assert [r["description"] for r in rows] == ["Good"]
    for line in (3, 4, 5):  # line numbers of the bad rows (header is line 1)
        assert re.search(rf"a\.csv\D{{1,12}}{line}\b", proc.stderr), proc.stderr


def test_K6_unknown_header_exits_2_without_output(tmp_path):
    x = write(tmp_path, "x.csv", "Who,What,When,HowLong\nAcme,Thing,2026-03-01,1\n")
    proc, out = run(tmp_path, [("desk", x)], rates(tmp_path))
    assert proc.returncode == 2
    assert not out.exists()


# --- K7 continued entries ----------------------------------------------

def test_K7_continued_across_trackers_is_joined(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + a_row("Acme", "Design", "01", "09:00", "10:00"))
    b = write(tmp_path, "b.csv", B_HDR + "acme,design ,2026-03-01T10:00:00,30\n")
    rows = merge_ok(tmp_path, [("desk", a), ("phone", b)], rates(tmp_path))
    assert len(rows) == 1
    assert rows[0]["minutes"] == "90" and rows[0]["session_id"]


def test_K7_two_minute_gap_joins_three_does_not_and_client_must_match(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR
              + a_row("Acme", "Design", "01", "09:00", "09:30")
              + a_row("Acme", "Design", "01", "09:32", "10:02")
              + a_row("Acme", "Design", "02", "09:00", "09:30")
              + a_row("Acme", "Design", "02", "09:33", "10:03")
              + a_row("Acme", "Build", "03", "09:00", "09:30")
              + a_row("Acme Labs", "Build", "03", "09:30", "10:00"))
    rows = merge_ok(tmp_path, [("desk", a)], rates(tmp_path))
    by_day = {}
    for r in rows:
        by_day.setdefault(r["date"], []).append(r)
    assert len(by_day["2026-03-01"]) == 1 and by_day["2026-03-01"][0]["session_id"]
    assert len(by_day["2026-03-02"]) == 2 and all(r["session_id"] == "" for r in by_day["2026-03-02"])
    assert len(by_day["2026-03-03"]) == 2 and all(r["session_id"] == "" for r in by_day["2026-03-03"])


def test_K7_takes_closest_successor_and_each_entry_once(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + a_row("Acme", "Design", "01", "09:00", "10:00"))
    b = write(tmp_path, "b.csv", B_HDR + "Acme,Design,2026-03-01T10:02:00,12\n"
              "Acme,Design,2026-03-01T10:00:00,30\n")
    rows = merge_ok(tmp_path, [("desk", a), ("phone", b)], rates(tmp_path))
    assert sorted((r["minutes"], bool(r["session_id"])) for r in rows) == [("12", False), ("90", True)]


def test_K7_successor_used_by_only_one_chain(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + a_row("Acme", "Design", "01", "09:00", "10:00")
              + a_row("Acme", "Design", "01", "09:30", "10:00"))
    b = write(tmp_path, "b.csv", B_HDR + "Acme,Design,2026-03-01T10:00:00,30\n")
    rows = merge_ok(tmp_path, [("desk", a), ("phone", b)], rates(tmp_path))
    assert len(rows) == 2
    assert len([r for r in rows if r["session_id"]]) == 1


# --- K8 / K9 pricing ---------------------------------------------------

def test_K8_rounds_up_to_6_after_joining_and_gap_not_billed(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR
              + a_row("Acme", "Design", "01", "09:00", "09:07")
              + a_row("Acme", "Design", "01", "09:07", "09:14")
              + a_row("Acme", "Review", "02", "09:00", "09:10")
              + a_row("Acme", "Review", "02", "09:12", "09:20")
              + a_row("Acme", "Email", "03", "09:00", "09:01"))
    rows = merge_ok(tmp_path, [("desk", a)], rates(tmp_path))
    assert [(r["date"], r["minutes"], r["amount"]) for r in rows] == [
        ("2026-03-01", "18", "18.00"), ("2026-03-02", "18", "18.00"), ("2026-03-03", "6", "6.00")]


def test_K9_first_rate_wins_case_insensitive_on_client_or_description(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR
              + a_row("Globex", "URGENT fix", "01", "09:00", "10:00")
              + a_row("ACME Corp", "Design", "02", "09:00", "10:00"))
    r = rates(tmp_path, [("urgent", "90.00"), ("globex", "50.00"), ("acme", "40.50")])
    rows = merge_ok(tmp_path, [("desk", a)], r)
    assert {x["client"]: x["amount"] for x in rows} == {"Globex": "90.00", "ACME Corp": "40.50"}


def test_K9_unmatched_is_zero_and_flagged(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + a_row("Initech", "TPS reports", "01", "09:00", "10:00"))
    proc, out = run(tmp_path, [("desk", a)], rates(tmp_path))
    assert proc.returncode == 0, proc.stderr
    rows = sessions(out)
    assert [x["amount"] for x in rows] == ["0.00"]
    assert "initech" in proc.stderr.lower() or "tps reports" in proc.stderr.lower(), proc.stderr


# --- K10 / K11 / K12 output --------------------------------------------

def test_K10_sorted_by_client_then_start_then_input_order(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR
              + a_row("Beta", "Late", "02", "15:00", "16:00")
              + a_row("Beta", "Z first in file", "02", "09:00", "10:00")
              + a_row("Beta", "A second in file", "02", "09:00", "10:00"))
    b = write(tmp_path, "b.csv", B_HDR + "acme,Later date,2026-03-03T08:00:00,60\n"
              "Beta,Early,2026-03-01T09:00:00,60\n")
    rows = merge_ok(tmp_path, [("desk", a), ("phone", b)], rates(tmp_path))
    assert [(x["client"], x["date"], x["description"]) for x in rows] == [
        ("acme", "2026-03-03", "Later date"),
        ("Beta", "2026-03-01", "Early"),
        ("Beta", "2026-03-02", "Z first in file"),
        ("Beta", "2026-03-02", "A second in file"),
        ("Beta", "2026-03-02", "Late"),
    ]


def test_K11_text_keeps_first_occurrence_casing(tmp_path):
    e1 = write(tmp_path, "e1.csv", A_HDR + a_row("  Acme Corp ", " Logo Design ", "01", "09:00", "10:00"))
    e2 = write(tmp_path, "e2.csv", A_HDR + a_row("ACME CORP", "LOGO DESIGN", "01", "09:00", "10:00"))
    rows = merge_ok(tmp_path, [("desk", e1), ("desk", e2)], rates(tmp_path))
    assert [(x["client"], x["description"]) for x in rows] == [("Acme Corp", "Logo Design")]


def test_K12_byte_identical_reruns(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + a_row("Acme", "Design", "01", "09:00", "10:00")
              + a_row("Globex", "Call", "01", "09:00", "09:20"))
    b = write(tmp_path, "b.csv", B_HDR + "Acme,Design,2026-03-01T10:01:00,30\n")
    r = rates(tmp_path)
    p1, o1 = run(tmp_path, [("desk", a), ("phone", b)], r, "s1.csv")
    p2, o2 = run(tmp_path, [("desk", a), ("phone", b)], r, "s2.csv")
    assert p1.returncode == p2.returncode == 0
    assert o1.read_bytes() == o2.read_bytes()
