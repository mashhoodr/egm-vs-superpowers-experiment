import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest

from stockmerge.cli import main
from stockmerge.core import normalise_sku

ROOT = Path(__file__).resolve().parents[1]
A = "Scanned At,SKU,Qty,Unit\n"
B = "timestamp,barcode,count,note\n"


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


def run(tmp_path, locations, rules="pattern,category\n"):
    rules_p = write(tmp_path, "rules.csv", rules)
    out = tmp_path / "out.csv"
    argv = ["merge"]
    for name, path in locations:
        argv += ["--location", f"{name}={path}"]
    argv += ["--rules", rules_p, "--out", str(out)]
    code = main(argv)
    rows = list(csv.reader(out.open())) if out.exists() else None
    return code, rows


def test_header_and_basic_units(tmp_path):
    a = write(tmp_path, "a.csv", A + "05/03/2026 14:30,SKU1,2,case\n05/03/2026 14:31,SKU1,-3,each\n")
    code, rows = run(tmp_path, [("floor", a)])
    assert code == 0
    assert rows[0] == ["location", "sku", "qty_each", "category", "move_id"]
    assert rows[1:] == [["floor", "SKU1", "24", "Uncategorised", ""],
                        ["floor", "SKU1", "-3", "Uncategorised", ""]]


def test_format_b_count_is_each_even_if_note_says_case(tmp_path):
    b = write(tmp_path, "b.csv", B + "2026-03-05T14:30:12,ABC,5,case of 12\n")
    _, rows = run(tmp_path, [("floor", b)])
    assert rows[1] == ["floor", "ABC", "5", "Uncategorised", ""]


def test_duplicates_across_exports_keep_max_count(tmp_path):
    line = "05/03/2026 14:30,X1,1,each\n"
    e1 = write(tmp_path, "e1.csv", A + line * 2)
    e2 = write(tmp_path, "e2.csv", A + line * 3)
    _, rows = run(tmp_path, [("floor", e1), ("floor", e2)])
    assert len(rows) - 1 == 3


def test_identical_rows_in_one_file_are_real(tmp_path):
    line = "05/03/2026 14:30,X1,1,each\n"
    e1 = write(tmp_path, "e1.csv", A + line * 2)
    _, rows = run(tmp_path, [("floor", e1)])
    assert len(rows) - 1 == 2


def test_same_scan_at_different_locations_not_duplicate(tmp_path):
    line = "05/03/2026 14:30,X1,1,each\n"
    e1 = write(tmp_path, "e1.csv", A + line)
    e2 = write(tmp_path, "e2.csv", A + line)
    _, rows = run(tmp_path, [("floor", e1), ("back", e2)])
    assert len(rows) - 1 == 2


def test_cross_format_duplicate_truncates_seconds_and_normalises_sku(tmp_path):
    a = write(tmp_path, "a.csv", A + "05/03/2026 14:30,00123,1,case\n")
    b = write(tmp_path, "b.csv", B + "2026-03-05T14:30:59,123,12,\n")
    _, rows = run(tmp_path, [("floor", a), ("floor", b)])
    assert rows[1:] == [["floor", "00123", "12", "Uncategorised", ""]]


def test_seconds_truncated_not_rounded(tmp_path):
    a = write(tmp_path, "a.csv", A + "05/03/2026 14:31,X,1,each\n")
    b = write(tmp_path, "b.csv", B + "2026-03-05T14:30:59,X,1,\n")
    _, rows = run(tmp_path, [("floor", a), ("floor", b)])
    assert len(rows) - 1 == 2


def test_spelling_from_first_location_argument(tmp_path):
    b = write(tmp_path, "b.csv", B + "2026-03-05T14:30:00,abc,1,\n")
    a = write(tmp_path, "a.csv", A + "05/03/2026 14:30, 0ABC ,1,each\n")
    _, rows = run(tmp_path, [("floor", b), ("floor", a)])
    assert rows[1:] == [["floor", "abc", "1", "Uncategorised", ""]]


def test_move_linked(tmp_path):
    f = write(tmp_path, "f.csv", A + "05/03/2026 10:00,X,-5,each\n")
    b = write(tmp_path, "b.csv", B + "2026-03-05T12:00:30,X,5,\n")
    _, rows = run(tmp_path, [("floor", f), ("back", b)])
    ids = {r[0]: r[4] for r in rows[1:]}
    assert ids["floor"] and ids["floor"] == ids["back"]


def test_move_window_exceeded(tmp_path):
    f = write(tmp_path, "f.csv", A + "05/03/2026 10:00,X,-5,each\n")
    b = write(tmp_path, "b.csv", A + "05/03/2026 12:01,X,5,each\n")
    _, rows = run(tmp_path, [("floor", f), ("back", b)])
    assert all(r[4] == "" for r in rows[1:])


def test_move_positive_may_precede_negative(tmp_path):
    f = write(tmp_path, "f.csv", A + "05/03/2026 10:00,X,-5,each\n")
    b = write(tmp_path, "b.csv", A + "05/03/2026 09:00,X,5,each\n")
    _, rows = run(tmp_path, [("floor", f), ("back", b)])
    assert rows[1][4] and rows[1][4] == rows[2][4]


def test_move_requires_different_location_and_exact_qty(tmp_path):
    f = write(tmp_path, "f.csv", A + "05/03/2026 10:00,X,-5,each\n05/03/2026 10:05,X,5,each\n")
    b = write(tmp_path, "b.csv", A + "05/03/2026 10:05,X,4,each\n")
    _, rows = run(tmp_path, [("floor", f), ("back", b)])
    assert all(r[4] == "" for r in rows[1:])


def test_move_case_vs_each_and_zeros(tmp_path):
    f = write(tmp_path, "f.csv", A + "05/03/2026 10:00,007,-1,case\n")
    b = write(tmp_path, "b.csv", B + "2026-03-05T10:10:00,7,12,\n")
    _, rows = run(tmp_path, [("floor", f), ("back", b)])
    assert rows[1][4] and rows[1][4] == rows[2][4]


def test_move_picks_closest_then_scan_order(tmp_path):
    f = write(tmp_path, "f.csv", A + "05/03/2026 10:00,X,-1,each\n")
    far = write(tmp_path, "far.csv", A + "05/03/2026 11:00,X,1,each\n")
    near1 = write(tmp_path, "n1.csv", A + "05/03/2026 10:30,X,1,each\n")
    near2 = write(tmp_path, "n2.csv", A + "05/03/2026 09:30,X,1,each\n")
    _, rows = run(tmp_path, [("floor", f), ("c", far), ("b", near1), ("a", near2)])
    by_loc = {r[0]: r[4] for r in rows[1:]}
    # 09:30 at 'a' and 10:30 at 'b' tie on gap; earlier timestamp wins.
    assert by_loc["a"] == by_loc["floor"] != ""
    assert by_loc["b"] == "" and by_loc["c"] == ""


def test_each_row_in_one_move_only(tmp_path):
    f = write(tmp_path, "f.csv", A + "05/03/2026 10:00,X,-1,each\n05/03/2026 10:01,X,-1,each\n")
    b = write(tmp_path, "b.csv", A + "05/03/2026 10:00,X,1,each\n")
    _, rows = run(tmp_path, [("floor", f), ("back", b)])
    ids = [r[4] for r in rows[1:] if r[4]]
    assert len(ids) == 2 and len(set(ids)) == 1


def test_duplicated_departure_pairs_once(tmp_path):
    line = "05/03/2026 10:00,X,-1,each\n"
    f1 = write(tmp_path, "f1.csv", A + line)
    f2 = write(tmp_path, "f2.csv", A + line)
    b = write(tmp_path, "b.csv", A + "05/03/2026 10:00,X,1,each\n05/03/2026 10:00,X,1,each\n")
    _, rows = run(tmp_path, [("floor", f1), ("floor", f2), ("back", b)])
    assert len(rows) - 1 == 3
    assert sum(1 for r in rows[1:] if r[4]) == 2


def test_categories_first_match_case_insensitive(tmp_path):
    a = write(tmp_path, "a.csv", A + "05/03/2026 10:00,drk-cola,1,each\n05/03/2026 10:00,ZZZ,1,each\n")
    rules = "pattern,category\nDRK,Drinks\ncola,Soda\n"
    _, rows = run(tmp_path, [("floor", a)], rules)
    cats = {r[1]: r[3] for r in rows[1:]}
    assert cats == {"drk-cola": "Drinks", "ZZZ": "Uncategorised"}


def test_sort_order(tmp_path):
    a = write(tmp_path, "a.csv", A + "05/03/2026 11:00,B,1,each\n05/03/2026 10:00,B,2,each\n05/03/2026 12:00,A,1,each\n")
    z = write(tmp_path, "z.csv", A + "05/03/2026 09:00,A,1,each\n")
    _, rows = run(tmp_path, [("zone", z), ("aisle", a)])
    assert [(r[0], r[1], r[2]) for r in rows[1:]] == [
        ("aisle", "A", "1"), ("aisle", "B", "2"), ("aisle", "B", "1"), ("zone", "A", "1")]


def test_bad_rows_skipped_with_warning(tmp_path, capsys):
    a = write(tmp_path, "a.csv", A + "31/02/2026 10:00,X,1,each\n05/03/2026 10:00,X,1.5,each\n"
              "05/03/2026 10:00,X,1,box\n05/03/2026 10:00,  ,1,each\n\n05/03/2026 10:00,OK,1,each\n")
    code, rows = run(tmp_path, [("floor", a)])
    assert code == 0
    assert [r[1] for r in rows[1:]] == ["OK"]
    err = capsys.readouterr().err
    assert err.count("a.csv:") == 5
    assert "a.csv:2" in err


def test_unknown_header_exits_2_no_output(tmp_path, capsys):
    a = write(tmp_path, "a.csv", "foo,bar\n1,2\n")
    code, rows = run(tmp_path, [("floor", a)])
    assert code == 2 and rows is None
    assert "unrecognised header" in capsys.readouterr().err


def test_zero_qty_rows_kept(tmp_path):
    a = write(tmp_path, "a.csv", A + "05/03/2026 10:00,X,0,each\n")
    _, rows = run(tmp_path, [("floor", a)])
    assert rows[1][2] == "0"


def test_normalise_sku():
    assert normalise_sku(" 00abc ") == "ABC"
    assert normalise_sku("000") == "0"


def test_deterministic_via_module(tmp_path):
    f = write(tmp_path, "f.csv", A + "05/03/2026 10:00,X,-5,each\n05/03/2026 10:00,Y,1,case\n")
    b = write(tmp_path, "b.csv", B + "2026-03-05T10:20:00,X,5,\n2026-03-05T10:20:00,X,5,\n")
    rules = write(tmp_path, "r.csv", "pattern,category\nx,Ex\n")
    outs = []
    for i in range(2):
        out = tmp_path / f"o{i}.csv"
        res = subprocess.run(
            [sys.executable, "-m", "stockmerge", "merge", "--location", f"floor={f}",
             "--location", f"back={b}", "--rules", rules, "--out", str(out)],
            cwd=ROOT, capture_output=True, text=True)
        assert res.returncode == 0, res.stderr
        outs.append(out.read_bytes())
    assert outs[0] == outs[1]


def test_format_b_note_with_unquoted_commas_kept(tmp_path):
    b = write(tmp_path, "b.csv", B + "2026-03-05T14:30:12,ABC,5,moved, see shelf 3\n")
    _, rows = run(tmp_path, [("floor", b)])
    assert rows[1] == ["floor", "ABC", "5", "Uncategorised", ""]
