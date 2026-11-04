"""Hidden acceptance tests. Run against an arm with:

    TXMERGE_ROOT=/path/to/arm/repo pytest -q _judge/hidden_tests

Each test is tagged with the stakeholder-key policy it checks (K1..K12).
Tests check policy outcomes, not incidental choices (e.g. transfer_id format).
"""
import csv
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(os.environ.get("TXMERGE_ROOT", Path(__file__).parent.parent / "reference"))

A_HDR = "Date,Description,Debit,Credit,Balance\n"
B_HDR = "Transaction Date,Posting Date,Details,Amount\n"
COLS = ["date", "account", "description", "amount", "category", "transfer_id"]


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


def rules(tmp_path, rows=()):
    return write(tmp_path, "rules.csv", "pattern,category\n" + "".join(f"{p},{c}\n" for p, c in rows))


def run(tmp_path, accounts, rules_path, out_name="ledger.csv"):
    out = tmp_path / out_name
    cmd = [sys.executable, "-m", "txmerge", "merge"]
    for name, path in accounts:
        cmd += ["--account", f"{name}={path}"]
    cmd += ["--rules", rules_path, "--out", str(out)]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
    return proc, out


def ledger(out):
    text = out.read_text()
    reader = csv.DictReader(io.StringIO(text))
    assert reader.fieldnames == COLS, f"bad header: {reader.fieldnames}"
    return list(reader)


def merge_ok(tmp_path, accounts, rules_path):
    proc, out = run(tmp_path, accounts, rules_path)
    assert proc.returncode == 0, proc.stderr
    return ledger(out)


# --- contract -----------------------------------------------------------

def test_contract_header_and_formatting(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + '05/03/2026,Coffee,3.5,,100\n')
    rows = merge_ok(tmp_path, [("current", a)], rules(tmp_path))
    assert rows == [{"date": "2026-03-05", "account": "current", "description": "Coffee",
                     "amount": "-3.50", "category": "Uncategorised", "transfer_id": ""}]


# --- K1 / K2 / K3 dedup ------------------------------------------------

def test_K1_overlap_dedup_with_normalised_description(tmp_path):
    e1 = write(tmp_path, "e1.csv", A_HDR + "01/03/2026,Grocery  Store,20.00,,0\n02/03/2026,Rent,500.00,,0\n")
    e2 = write(tmp_path, "e2.csv", A_HDR + "02/03/2026,rent ,500.00,,0\n03/03/2026,Gym,30.00,,0\n")
    rows = merge_ok(tmp_path, [("cur", e1), ("cur", e2)], rules(tmp_path))
    assert [(r["date"], r["amount"]) for r in rows] == [
        ("2026-03-01", "-20.00"), ("2026-03-02", "-500.00"), ("2026-03-03", "-30.00")]


def test_K2_identical_rows_within_one_export_are_kept(tmp_path):
    e1 = write(tmp_path, "e1.csv", A_HDR + "01/03/2026,Coffee,3.50,,0\n01/03/2026,Coffee,3.50,,0\n")
    rows = merge_ok(tmp_path, [("cur", e1)], rules(tmp_path))
    assert len(rows) == 2


def test_K2_cross_export_count_is_max_not_sum(tmp_path):
    coffee = "01/03/2026,Coffee,3.50,,0\n"
    e1 = write(tmp_path, "e1.csv", A_HDR + coffee * 2)
    e2 = write(tmp_path, "e2.csv", A_HDR + coffee * 3)
    rows = merge_ok(tmp_path, [("cur", e1), ("cur", e2)], rules(tmp_path))
    assert len(rows) == 3


def test_K3_different_accounts_never_dedup(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026,Coffee,3.50,,0\n")
    b = write(tmp_path, "b.csv", B_HDR + "2026-03-01,2026-03-02,Coffee,-3.50\n")
    rows = merge_ok(tmp_path, [("cur", a), ("card", b)], rules(tmp_path))
    assert len(rows) == 2


# --- K4 / K5 / K6 parsing ----------------------------------------------

def test_K4_format_b_uses_transaction_date(tmp_path):
    b = write(tmp_path, "b.csv", B_HDR + "2026-03-01,2026-03-04,Book,-12.00\n")
    rows = merge_ok(tmp_path, [("card", b)], rules(tmp_path))
    assert rows[0]["date"] == "2026-03-01"


def test_K5_debit_credit_signs_and_thousands(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + '01/03/2026,Salary,,"2,500.00",0\n02/03/2026,Laptop,"1,250.00",,0\n')
    rows = merge_ok(tmp_path, [("cur", a)], rules(tmp_path))
    assert [r["amount"] for r in rows] == ["2500.00", "-1250.00"]


def test_K5_malformed_row_skipped_with_warning(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026,Good,5.00,,0\n02/03/2026,Empty,,,0\nnot-a-date,Bad,1.00,,0\n")
    proc, out = run(tmp_path, [("cur", a)], rules(tmp_path))
    assert proc.returncode == 0, proc.stderr
    rows = ledger(out)
    assert [r["description"] for r in rows] == ["Good"]
    import re
    for line in (3, 4):  # line numbers of the bad rows (header is line 1)
        assert re.search(rf"a\.csv\D{{1,12}}{line}\b", proc.stderr), proc.stderr


def test_K6_unknown_header_exits_2_without_output(tmp_path):
    x = write(tmp_path, "x.csv", "When,What,HowMuch\n2026-03-01,Thing,1\n")
    proc, out = run(tmp_path, [("cur", x)], rules(tmp_path))
    assert proc.returncode == 2
    assert not out.exists()


# --- K7 / K8 transfers -------------------------------------------------

def test_K7_transfer_within_3_days_is_linked_and_not_ruled(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026,Payment to card,200.00,,0\n")
    b = write(tmp_path, "b.csv", B_HDR + "2026-03-04,2026-03-04,Payment received,200.00\n")
    r = rules(tmp_path, [("payment", "Bills")])
    rows = merge_ok(tmp_path, [("cur", a), ("card", b)], r)
    assert len(rows) == 2
    assert rows[0]["transfer_id"] and rows[0]["transfer_id"] == rows[1]["transfer_id"]
    assert {x["category"] for x in rows} == {"Transfer"}


def test_K7_four_days_apart_is_not_a_transfer(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026,Payment to card,200.00,,0\n")
    b = write(tmp_path, "b.csv", B_HDR + "2026-03-05,2026-03-05,Payment received,200.00\n")
    rows = merge_ok(tmp_path, [("cur", a), ("card", b)], rules(tmp_path))
    assert all(x["transfer_id"] == "" for x in rows)
    assert {x["category"] for x in rows} == {"Uncategorised"}


def test_K7_same_account_never_a_transfer(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026,Out,50.00,,0\n02/03/2026,Refund,,50.00,0\n")
    rows = merge_ok(tmp_path, [("cur", a)], rules(tmp_path))
    assert all(x["transfer_id"] == "" for x in rows)


def test_K8_pairs_closest_date_and_each_row_once(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026,To savings,100.00,,0\n")
    s = write(tmp_path, "s.csv", A_HDR + "03/03/2026,From current,,100.00,0\n02/03/2026,From current,,100.00,0\n")
    rows = merge_ok(tmp_path, [("cur", a), ("sav", s)], rules(tmp_path))
    by = {(x["account"], x["date"]): x for x in rows}
    out_id = by[("cur", "2026-03-01")]["transfer_id"]
    assert out_id and by[("sav", "2026-03-02")]["transfer_id"] == out_id
    assert by[("sav", "2026-03-03")]["transfer_id"] == ""


def test_K8_inflow_used_by_only_one_outflow(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026,To savings,100.00,,0\n02/03/2026,To savings,100.00,,0\n")
    s = write(tmp_path, "s.csv", A_HDR + "02/03/2026,From current,,100.00,0\n")
    rows = merge_ok(tmp_path, [("cur", a), ("sav", s)], rules(tmp_path))
    linked = [x for x in rows if x["transfer_id"]]
    assert len(linked) == 2
    assert len({x["transfer_id"] for x in linked}) == 1


# --- K9 rules ----------------------------------------------------------

def test_K9_first_rule_wins_case_insensitive(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026,TESCO Express,9.00,,0\n02/03/2026,Netflix,8.00,,0\n")
    r = rules(tmp_path, [("tesco express", "Snacks"), ("tesco", "Groceries")])
    rows = merge_ok(tmp_path, [("cur", a)], r)
    assert [x["category"] for x in rows] == ["Snacks", "Uncategorised"]


# --- K10 / K11 / K12 output --------------------------------------------

def test_K10_sorted_by_date_then_account_then_input_order(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "02/03/2026,Z first in file,1.00,,0\n02/03/2026,A second in file,2.00,,0\n01/03/2026,Early,3.00,,0\n")
    b = write(tmp_path, "b.csv", B_HDR + "2026-03-02,2026-03-02,Card thing,-4.00\n")
    rows = merge_ok(tmp_path, [("zcur", a), ("acard", b)], rules(tmp_path))
    assert [(x["date"], x["account"], x["description"]) for x in rows] == [
        ("2026-03-01", "zcur", "Early"),
        ("2026-03-02", "acard", "Card thing"),
        ("2026-03-02", "zcur", "Z first in file"),
        ("2026-03-02", "zcur", "A second in file"),
    ]


def test_K11_description_keeps_first_occurrence_casing(tmp_path):
    e1 = write(tmp_path, "e1.csv", A_HDR + "01/03/2026,  Corner Shop ,4.00,,0\n")
    e2 = write(tmp_path, "e2.csv", A_HDR + "01/03/2026,CORNER SHOP,4.00,,0\n")
    rows = merge_ok(tmp_path, [("cur", e1), ("cur", e2)], rules(tmp_path))
    assert [x["description"] for x in rows] == ["Corner Shop"]


def test_K12_byte_identical_reruns(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026,To savings,100.00,,0\n01/03/2026,Coffee,3.50,,0\n")
    s = write(tmp_path, "s.csv", A_HDR + "02/03/2026,From current,,100.00,0\n")
    r = rules(tmp_path, [("coffee", "Food")])
    p1, o1 = run(tmp_path, [("cur", a), ("sav", s)], r, "l1.csv")
    p2, o2 = run(tmp_path, [("cur", a), ("sav", s)], r, "l2.csv")
    assert p1.returncode == p2.returncode == 0
    assert o1.read_bytes() == o2.read_bytes()
