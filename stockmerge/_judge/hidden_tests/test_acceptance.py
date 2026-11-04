"""Hidden acceptance tests. Run against an arm with:

    STOCKMERGE_ROOT=/path/to/arm/repo pytest -q _judge/hidden_tests

Each test is tagged with the stakeholder-key policy it checks (K1..K12).
Tests check policy outcomes, not incidental choices (e.g. move_id format).
"""
import csv
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(os.environ.get("STOCKMERGE_ROOT", Path(__file__).parent.parent / "reference"))

A_HDR = "Scanned At,SKU,Qty,Unit\n"
B_HDR = "timestamp,barcode,count,note\n"
COLS = ["location", "sku", "qty_each", "category", "move_id"]


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


def rules(tmp_path, rows=()):
    return write(tmp_path, "rules.csv", "pattern,category\n" + "".join(f"{p},{c}\n" for p, c in rows))


def run(tmp_path, locations, rules_path, out_name="inventory.csv"):
    out = tmp_path / out_name
    cmd = [sys.executable, "-m", "stockmerge", "merge"]
    for name, path in locations:
        cmd += ["--location", f"{name}={path}"]
    cmd += ["--rules", rules_path, "--out", str(out)]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60)
    return proc, out


def inventory(out):
    text = out.read_text()
    reader = csv.DictReader(io.StringIO(text))
    assert reader.fieldnames == COLS, f"bad header: {reader.fieldnames}"
    return list(reader)


def merge_ok(tmp_path, locations, rules_path):
    proc, out = run(tmp_path, locations, rules_path)
    assert proc.returncode == 0, proc.stderr
    return inventory(out)


# --- contract -----------------------------------------------------------

def test_contract_header_and_formatting(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "05/03/2026 14:30,COLA-330,3,each\n")
    rows = merge_ok(tmp_path, [("shop", a)], rules(tmp_path))
    assert rows == [{"location": "shop", "sku": "COLA-330", "qty_each": "3",
                     "category": "Uncategorised", "move_id": ""}]


# --- K1 / K2 / K3 dedup ------------------------------------------------

def test_K1_overlap_dedup_with_normalised_sku(tmp_path):
    e1 = write(tmp_path, "e1.csv", A_HDR + "01/03/2026 09:00, cola-330 ,6,each\n01/03/2026 09:05,00123,2,each\n")
    e2 = write(tmp_path, "e2.csv", A_HDR + "01/03/2026 09:00,COLA-330,6,each\n01/03/2026 09:05,123,2,each\n"
               "01/03/2026 09:10,CHIPS,1,each\n")
    rows = merge_ok(tmp_path, [("back", e1), ("back", e2)], rules(tmp_path))
    assert sorted(int(r["qty_each"]) for r in rows) == [1, 2, 6]


def test_K2_identical_rows_within_one_export_are_kept(tmp_path):
    e1 = write(tmp_path, "e1.csv", A_HDR + "01/03/2026 09:00,COLA-330,6,each\n01/03/2026 09:00,COLA-330,6,each\n")
    rows = merge_ok(tmp_path, [("shop", e1)], rules(tmp_path))
    assert len(rows) == 2


def test_K2_cross_export_count_is_max_not_sum(tmp_path):
    scan = "01/03/2026 09:00,COLA-330,6,each\n"
    e1 = write(tmp_path, "e1.csv", A_HDR + scan * 2)
    e2 = write(tmp_path, "e2.csv", A_HDR + scan * 3)
    rows = merge_ok(tmp_path, [("shop", e1), ("shop", e2)], rules(tmp_path))
    assert len(rows) == 3


def test_K3_different_locations_never_dedup(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026 09:00,COLA-330,6,each\n")
    b = write(tmp_path, "b.csv", B_HDR + "2026-03-01T09:00:00,COLA-330,6,\n")
    rows = merge_ok(tmp_path, [("shop", a), ("back", b)], rules(tmp_path))
    assert len(rows) == 2


# --- K4 / K5 / K6 parsing ----------------------------------------------

def test_K4_seconds_dropped_and_note_ignored(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "05/03/2026 14:30,COLA-330,6,each\n")
    b = write(tmp_path, "b.csv", B_HDR + "2026-03-05T14:30:59,COLA-330,6,\n2026-03-05T15:00:00,CHIPS,2,case\n")
    rows = merge_ok(tmp_path, [("shop", a), ("shop", b)], rules(tmp_path))
    assert sorted((r["sku"], r["qty_each"]) for r in rows) == [("CHIPS", "2"), ("COLA-330", "6")]


def test_K5_case_converts_to_twelve_eaches(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026 09:00,COLA-330,2,case\n01/03/2026 09:01,CHIPS,-1, CASE\n"
              "01/03/2026 09:02,GUM,5,each\n")
    rows = merge_ok(tmp_path, [("back", a)], rules(tmp_path))
    assert {r["sku"]: r["qty_each"] for r in rows} == {"COLA-330": "24", "CHIPS": "-12", "GUM": "5"}


def test_K5_malformed_row_skipped_with_warning(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026 09:00,GOOD,5,each\n01/03/2026 09:01,HALF,1.5,each\n"
              "01/03/2026 09:02,BOX,1,box\nnot-a-date,BAD,1,each\n")
    proc, out = run(tmp_path, [("shop", a)], rules(tmp_path))
    assert proc.returncode == 0, proc.stderr
    rows = inventory(out)
    assert [r["sku"] for r in rows] == ["GOOD"]
    import re
    for line in (3, 4, 5):  # line numbers of the bad rows (header is line 1)
        assert re.search(rf"a\.csv\D{{1,12}}{line}\b", proc.stderr), proc.stderr


def test_K6_unknown_header_exits_2_without_output(tmp_path):
    x = write(tmp_path, "x.csv", "When,Item,HowMany\n2026-03-01,Thing,1\n")
    proc, out = run(tmp_path, [("shop", x)], rules(tmp_path))
    assert proc.returncode == 2
    assert not out.exists()


# --- K7 / K8 moves -----------------------------------------------------

def test_K7_move_within_2_hours_is_linked_and_not_ruled(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026 10:00,COLA-330,-4,each\n")
    b = write(tmp_path, "b.csv", B_HDR + "2026-03-01T12:00:00,COLA-330,4,\n")
    r = rules(tmp_path, [("cola", "Soft drinks")])
    rows = merge_ok(tmp_path, [("back", a), ("shop", b)], r)
    assert len(rows) == 2
    assert rows[0]["move_id"] and rows[0]["move_id"] == rows[1]["move_id"]
    assert {x["category"] for x in rows} == {"Move"}


def test_K7_over_2_hours_is_not_a_move(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026 10:00,COLA-330,-4,each\n")
    b = write(tmp_path, "b.csv", B_HDR + "2026-03-01T12:01:00,COLA-330,4,\n")
    rows = merge_ok(tmp_path, [("back", a), ("shop", b)], rules(tmp_path))
    assert all(x["move_id"] == "" for x in rows)
    assert {x["category"] for x in rows} == {"Uncategorised"}


def test_K7_same_location_never_a_move(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026 10:00,COLA-330,-4,each\n01/03/2026 10:30,COLA-330,4,each\n")
    rows = merge_ok(tmp_path, [("shop", a)], rules(tmp_path))
    assert all(x["move_id"] == "" for x in rows)


def test_K8_pairs_closest_time_and_each_row_once(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026 10:00,COLA-330,-6,each\n")
    s = write(tmp_path, "s.csv", A_HDR + "01/03/2026 11:30,COLA-330,6,each\n")
    w = write(tmp_path, "w.csv", A_HDR + "01/03/2026 10:45,COLA-330,6,each\n")
    rows = merge_ok(tmp_path, [("back", a), ("shop", s), ("window", w)], rules(tmp_path))
    by = {x["location"]: x for x in rows}
    out_id = by["back"]["move_id"]
    assert out_id and by["window"]["move_id"] == out_id
    assert by["shop"]["move_id"] == ""


def test_K8_positive_used_by_only_one_negative(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026 10:00,COLA-330,-6,each\n01/03/2026 10:30,COLA-330,-6,each\n")
    s = write(tmp_path, "s.csv", A_HDR + "01/03/2026 10:15,COLA-330,6,each\n")
    rows = merge_ok(tmp_path, [("back", a), ("shop", s)], rules(tmp_path))
    linked = [x for x in rows if x["move_id"]]
    assert len(linked) == 2
    assert len({x["move_id"] for x in linked}) == 1


# --- K9 rules ----------------------------------------------------------

def test_K9_first_rule_wins_case_insensitive(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026 09:00,DIET-COLA-330,1,each\n01/03/2026 09:01,GUM,1,each\n")
    r = rules(tmp_path, [("diet-cola", "Diet drinks"), ("COLA", "Soft drinks")])
    rows = merge_ok(tmp_path, [("shop", a)], r)
    assert {x["sku"]: x["category"] for x in rows} == {"DIET-COLA-330": "Diet drinks", "GUM": "Uncategorised"}


# --- K10 / K11 / K12 output --------------------------------------------

def test_K10_sorted_by_location_then_sku_then_time_then_input_order(tmp_path):
    s = write(tmp_path, "s.csv", A_HDR + "01/03/2026 10:00,COLA,1,each\n01/03/2026 11:00,APPLE,2,each\n"
              "01/03/2026 09:00,COLA,3,each\n01/03/2026 09:00,COLA,7,each\n")
    b = write(tmp_path, "b.csv", B_HDR + "2026-03-01T12:00:00,ZEBRA,4,\n")
    rows = merge_ok(tmp_path, [("shop", s), ("back", b)], rules(tmp_path))
    assert [(x["location"], x["sku"], x["qty_each"]) for x in rows] == [
        ("back", "ZEBRA", "4"),
        ("shop", "APPLE", "2"),
        ("shop", "COLA", "3"),
        ("shop", "COLA", "7"),
        ("shop", "COLA", "1"),
    ]


def test_K11_sku_keeps_first_occurrence_text(tmp_path):
    e1 = write(tmp_path, "e1.csv", A_HDR + "01/03/2026 09:00,  Cola-330 ,4,each\n01/03/2026 09:05,00123,2,each\n")
    e2 = write(tmp_path, "e2.csv", B_HDR + "2026-03-01T09:00:10,COLA-330,4,\n2026-03-01T09:05:00,123,2,\n")
    rows = merge_ok(tmp_path, [("shop", e1), ("shop", e2)], rules(tmp_path))
    assert sorted(x["sku"] for x in rows) == ["00123", "Cola-330"]


def test_K12_byte_identical_reruns(tmp_path):
    a = write(tmp_path, "a.csv", A_HDR + "01/03/2026 10:00,COLA-330,-6,each\n01/03/2026 10:00,GUM,3,each\n")
    s = write(tmp_path, "s.csv", A_HDR + "01/03/2026 10:30,COLA-330,6,each\n")
    r = rules(tmp_path, [("gum", "Confectionery")])
    p1, o1 = run(tmp_path, [("back", a), ("shop", s)], r, "i1.csv")
    p2, o2 = run(tmp_path, [("back", a), ("shop", s)], r, "i2.csv")
    assert p1.returncode == p2.returncode == 0
    assert o1.read_bytes() == o2.read_bytes()
