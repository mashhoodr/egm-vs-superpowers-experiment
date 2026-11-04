import csv
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

A_HEADER = "Date,Description,Debit,Credit,Balance\n"
B_HEADER = "Transaction Date,Posting Date,Details,Amount\n"
OUT_HEADER = ["date", "account", "description", "amount", "category", "transfer_id"]


def write(path: Path, text: str) -> str:
    path.write_text(text, encoding="utf-8")
    return str(path)


def run(tmp_path, accounts, rules="pattern,category\n"):
    rules_path = write(tmp_path / "rules.csv", rules)
    out = tmp_path / "ledger.csv"
    cmd = [sys.executable, "-m", "txmerge", "merge"]
    for name, path in accounts:
        cmd += ["--account", f"{name}={path}"]
    cmd += ["--rules", rules_path, "--out", str(out)]
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    rows = None
    if out.exists():
        with open(out, newline="") as fh:
            rows = list(csv.reader(fh))
    return proc, rows


def body(rows):
    assert rows[0] == OUT_HEADER
    return [dict(zip(OUT_HEADER, r)) for r in rows[1:]]


# --- parsing -------------------------------------------------------------

def test_format_a_parsing_and_thousands(tmp_path):
    a = write(tmp_path / "a.csv", A_HEADER +
              '05/03/2024,Rent,"1,250.00",,100.00\n'
              "06/03/2024,Salary,,2000,2100.00\n")
    proc, rows = run(tmp_path, [("current", a)])
    assert proc.returncode == 0, proc.stderr
    got = body(rows)
    assert [(r["date"], r["amount"]) for r in got] == [
        ("2024-03-05", "-1250.00"), ("2024-03-06", "2000.00")]
    assert all(r["category"] == "Uncategorised" and r["transfer_id"] == "" for r in got)


def test_format_b_uses_transaction_date_and_signed_amount(tmp_path):
    b = write(tmp_path / "b.csv", B_HEADER +
              "2024-03-01,2024-03-04,Coffee Shop,-3.5\n"
              "2024-03-02,2024-03-05,Refund,10.00\n")
    proc, rows = run(tmp_path, [("card", b)])
    assert proc.returncode == 0
    got = body(rows)
    assert [(r["date"], r["amount"]) for r in got] == [
        ("2024-03-01", "-3.50"), ("2024-03-02", "10.00")]


def test_header_with_bom_is_detected(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text("﻿" + A_HEADER + "01/01/2024,X,1.00,,0\n", encoding="utf-8")
    proc, rows = run(tmp_path, [("current", str(p))])
    assert proc.returncode == 0
    assert len(body(rows)) == 1


# --- dedupe --------------------------------------------------------------

def test_overlapping_exports_deduplicated(tmp_path):
    e1 = write(tmp_path / "e1.csv", A_HEADER +
               "01/03/2024,Tesco,10.00,,90\n"
               "02/03/2024,Shell,40.00,,50\n")
    e2 = write(tmp_path / "e2.csv", A_HEADER +
               "02/03/2024,Shell,40.00,,50\n"
               "03/03/2024,Boots,5.00,,45\n")
    proc, rows = run(tmp_path, [("current", e1), ("current", e2)])
    got = body(rows)
    assert [r["description"] for r in got] == ["Tesco", "Shell", "Boots"]


def test_identical_rows_in_one_file_are_kept(tmp_path):
    e1 = write(tmp_path / "e1.csv", B_HEADER +
               "2024-03-01,2024-03-02,Coffee,-3.50\n"
               "2024-03-01,2024-03-02,Coffee,-3.50\n")
    proc, rows = run(tmp_path, [("card", e1)])
    assert len(body(rows)) == 2


def test_overlap_counts_take_max_not_sum(tmp_path):
    two = B_HEADER + "2024-03-01,2024-03-02,Coffee,-3.50\n" * 2
    three = B_HEADER + "2024-03-01,2024-03-03,Coffee,-3.50\n" * 3
    e1 = write(tmp_path / "e1.csv", two)
    e2 = write(tmp_path / "e2.csv", three)
    _, rows = run(tmp_path, [("card", e1), ("card", e2)])
    assert len(body(rows)) == 3
    _, rows = run(tmp_path, [("card", e1), ("card", e1)])
    assert len(body(rows)) == 2


def test_description_normalisation_for_dedupe(tmp_path):
    e1 = write(tmp_path / "e1.csv", A_HEADER + "01/03/2024,TESCO  Stores,10.00,,0\n")
    e2 = write(tmp_path / "e2.csv", A_HEADER + "01/03/2024,  tesco stores ,10.00,,99\n")
    _, rows = run(tmp_path, [("current", e1), ("current", e2)])
    got = body(rows)
    assert len(got) == 1
    assert got[0]["description"] == "TESCO  Stores"  # first by argument order


def test_different_accounts_never_dedupe(tmp_path):
    e1 = write(tmp_path / "e1.csv", A_HEADER + "01/03/2024,Tesco,10.00,,0\n")
    _, rows = run(tmp_path, [("one", e1), ("two", e1)])
    assert len(body(rows)) == 2


def test_different_amount_or_date_not_duplicate(tmp_path):
    e1 = write(tmp_path / "e1.csv", A_HEADER + "01/03/2024,Tesco,10.00,,0\n")
    e2 = write(tmp_path / "e2.csv", A_HEADER +
               "01/03/2024,Tesco,10.01,,0\n02/03/2024,Tesco,10.00,,0\n")
    _, rows = run(tmp_path, [("c", e1), ("c", e2)])
    assert len(body(rows)) == 3


# --- transfers -----------------------------------------------------------

def test_transfer_linked_within_three_days(tmp_path):
    cur = write(tmp_path / "cur.csv", A_HEADER + "01/03/2024,To card,500.00,,0\n")
    card = write(tmp_path / "card.csv", B_HEADER + "2024-03-04,2024-03-05,Payment thanks,500.00\n")
    _, rows = run(tmp_path, [("current", cur), ("card", card)],
                  rules="pattern,category\ncard,Shopping\n")
    got = body(rows)
    assert {r["category"] for r in got} == {"Transfer"}
    assert got[0]["transfer_id"] and got[0]["transfer_id"] == got[1]["transfer_id"]


def test_transfer_outside_window_not_linked(tmp_path):
    cur = write(tmp_path / "cur.csv", A_HEADER + "01/03/2024,To card,500.00,,0\n")
    card = write(tmp_path / "card.csv", B_HEADER + "2024-03-05,2024-03-05,Payment,500.00\n")
    _, rows = run(tmp_path, [("current", cur), ("card", card)])
    assert all(r["transfer_id"] == "" for r in body(rows))


def test_same_account_not_a_transfer(tmp_path):
    cur = write(tmp_path / "cur.csv", A_HEADER +
                "01/03/2024,Out,50.00,,0\n01/03/2024,Back,,50.00,0\n")
    _, rows = run(tmp_path, [("current", cur)])
    assert all(r["transfer_id"] == "" for r in body(rows))


def test_transfer_picks_closest_then_first_and_one_use_only(tmp_path):
    cur = write(tmp_path / "cur.csv", A_HEADER +
                "05/03/2024,Out1,100.00,,0\n"
                "05/03/2024,Out2,100.00,,0\n")
    sav = write(tmp_path / "sav.csv", A_HEADER +
                "03/03/2024,InFar,,100.00,0\n"
                "06/03/2024,InNear,,100.00,0\n"
                "07/03/2024,InTiedLater,,100.00,0\n")
    _, rows = run(tmp_path, [("current", cur), ("savings", sav)])
    got = {r["description"]: r for r in body(rows)}
    assert got["Out1"]["transfer_id"] == got["InNear"]["transfer_id"] != ""
    # Out2: InFar and InTiedLater both 2 days away; InFar is first in output order
    assert got["Out2"]["transfer_id"] == got["InFar"]["transfer_id"] != ""
    assert got["InTiedLater"]["transfer_id"] == ""
    assert got["Out1"]["transfer_id"] != got["Out2"]["transfer_id"]


# --- categorisation ------------------------------------------------------

def test_rules_first_match_case_insensitive_substring(tmp_path):
    a = write(tmp_path / "a.csv", A_HEADER +
              "01/03/2024,TESCO EXPRESS,10.00,,0\n"
              "02/03/2024,Mystery,1.00,,0\n")
    _, rows = run(tmp_path, [("c", a)],
                  rules="pattern,category\ntesco express,Convenience\nTesco,Groceries\n")
    got = body(rows)
    assert [r["category"] for r in got] == ["Convenience", "Uncategorised"]


# --- ordering & determinism ---------------------------------------------

def test_sort_by_date_then_account_then_line(tmp_path):
    z = write(tmp_path / "z.csv", A_HEADER + "02/03/2024,Z2,1.00,,0\n01/03/2024,Z1,1.00,,0\n")
    a = write(tmp_path / "a.csv", A_HEADER + "02/03/2024,A2b,2.00,,0\n02/03/2024,A2,1.00,,0\n")
    _, rows = run(tmp_path, [("zeta", z), ("alpha", a)])
    assert [r["description"] for r in body(rows)] == ["Z1", "A2b", "A2", "Z2"]


def test_rerun_is_byte_identical(tmp_path):
    cur = write(tmp_path / "cur.csv", A_HEADER +
                "01/03/2024,To card,500.00,,0\n02/03/2024,Tesco,12.00,,0\n")
    card = write(tmp_path / "card.csv", B_HEADER + "2024-03-02,2024-03-03,Payment,500.00\n")
    run(tmp_path, [("current", cur), ("card", card)])
    first = (tmp_path / "ledger.csv").read_bytes()
    run(tmp_path, [("current", cur), ("card", card)])
    assert (tmp_path / "ledger.csv").read_bytes() == first


# --- errors --------------------------------------------------------------

def test_malformed_rows_skipped_with_warning(tmp_path):
    a = write(tmp_path / "a.csv", A_HEADER +
              "01/03/2024,Good,1.00,,0\n"
              "31/02/2024,BadDate,1.00,,0\n"
              "02/03/2024,Both,1.00,2.00,0\n"
              "02/03/2024,Neither,,,0\n"
              "02/03/2024,BadAmt,abc,,0\n")
    proc, rows = run(tmp_path, [("c", a)])
    assert proc.returncode == 0
    assert [r["description"] for r in body(rows)] == ["Good"]
    for line in (3, 4, 5, 6):
        assert f"a.csv:{line}" in proc.stderr


def test_unknown_header_exits_2_and_writes_nothing(tmp_path):
    bad = write(tmp_path / "bad.csv", "foo,bar\n1,2\n")
    proc, rows = run(tmp_path, [("c", bad)])
    assert proc.returncode == 2
    assert rows is None
    assert "bad.csv" in proc.stderr


def test_missing_file_exits_2_and_writes_nothing(tmp_path):
    proc, rows = run(tmp_path, [("c", str(tmp_path / "nope.csv"))])
    assert proc.returncode == 2
    assert rows is None
