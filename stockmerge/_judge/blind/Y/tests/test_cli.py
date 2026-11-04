import os

import pytest

from stockmerge import cli

A = "Scanned At,SKU,Qty,Unit\n"
B = "timestamp,barcode,count,note\n"
HEADER = "location,sku,qty_each,category,move_id\n"

WORKED_OUT = (
    "location,sku,qty_each,category,move_id\n"
    "back,ABC,-6,Move,M0001\n"
    "shop,0042,-1,Spares,\n"
    "shop,abc,6,Move,M0001\n"
    "shop,abc,6,Uncategorised,\n"
)
WORKED_SUMMARY = (
    "stockmerge: read 5 rows, removed 1 duplicates, skipped 0 rows, linked 1 moves, wrote 4 rows"
)


@pytest.fixture
def rules(write_file):
    return write_file("rules.csv", "pattern,category\n")


@pytest.fixture
def worked(write_file):
    b = write_file("b.csv", A + "05/03/2026 10:05,ABC,-6,each\n")
    s1 = write_file("s1.csv", A + "05/03/2026 11:40,abc,6,each\n05/03/2026 11:40,abc,6,each\n")
    s2 = write_file("s2.csv", B + "2026-03-05T11:40:30,abc,6,\n2026-03-05T12:10:00,0042,-1,\n")
    r = write_file("rules.csv", "pattern,category\n42,Spares\n")
    return ["--location", f"back={b}", "--location", f"shop={s1}",
            "--location", f"shop={s2}", "--rules", r]


def merge(run_cli, *args):
    return run_cli("merge", *args)


# R1.1
def test_missing_rules(run_cli, write_file, tmp_path):
    a = write_file("a.csv", A)
    code, out, err = merge(run_cli, "--location", f"shop={a}", "--out", str(tmp_path / "o.csv"))
    assert code == 2 and err.startswith("usage: stockmerge") and out == ""


def test_help(run_cli):
    code, out, err = run_cli("merge", "--help")
    assert code == 0 and out.strip()


def test_abbreviation_rejected(run_cli, write_file, rules, tmp_path):
    a = write_file("a.csv", A)
    code, _, _ = merge(run_cli, "--loc", f"shop={a}", "--rules", rules, "--out", str(tmp_path / "o.csv"))
    assert code == 2


# R1.2
def test_location_without_equals(run_cli, rules, tmp_path):
    code, _, err = merge(run_cli, "--location", "shop", "--rules", rules, "--out", str(tmp_path / "o.csv"))
    assert code == 2 and "expected NAME=PATH" in err


@pytest.mark.parametrize("value", ["=a.csv", "shop="])
def test_location_empty_parts(run_cli, rules, tmp_path, value):
    code, _, _ = merge(run_cli, "--location", value, "--rules", rules, "--out", str(tmp_path / "o.csv"))
    assert code == 2


def test_location_trimmed(run_cli, write_file, rules, tmp_path, read_out):
    a = write_file("a.csv", A + "05/03/2026 10:00,X,1,each\n")
    out = str(tmp_path / "o.csv")
    code, _, _ = merge(run_cli, "--location", f" shop = {a} ", "--rules", rules, "--out", out)
    assert code == 0 and read_out(out)[0]["location"] == "shop"


# R1.3
def test_same_path_twice(run_cli, write_file, rules, tmp_path):
    a = write_file("a.csv", A + "05/03/2026 10:00,X,1,each\n05/03/2026 10:00,X,1,each\n")
    o1, o2 = str(tmp_path / "o1.csv"), str(tmp_path / "o2.csv")
    merge(run_cli, "--location", f"shop={a}", "--rules", rules, "--out", o1)
    code, _, err = merge(run_cli, "--location", f"shop={a}", "--location", f"shop={a}",
                         "--rules", rules, "--out", o2)
    assert code == 0
    assert open(o1, "rb").read() == open(o2, "rb").read()
    assert "removed 2 duplicates" in err


# R1.4
def test_similar_names_warn(run_cli, write_file, rules, tmp_path):
    a = write_file("a.csv", A)
    b = write_file("b.csv", A)
    code, _, err = merge(run_cli, "--location", f"Shop  Floor={a}", "--location", f"shop floor={b}",
                         "--rules", rules, "--out", str(tmp_path / "o.csv"))
    assert code == 0 and "differ only by case or spaces" in err


# R1.5
def test_same_file_two_names(run_cli, write_file, rules, tmp_path):
    x = write_file("x.csv", A)
    code, _, err = merge(run_cli, "--location", f"a={x}", "--location", f"b={x}",
                         "--rules", rules, "--out", str(tmp_path / "o.csv"))
    assert code == 0 and "is given for both" in err


# R2.1
def test_missing_input(run_cli, rules, tmp_path):
    out = tmp_path / "o.csv"
    code, _, err = merge(run_cli, "--location", f"shop={tmp_path / 'nope.csv'}", "--rules", rules, "--out", str(out))
    assert code == 2 and "cannot read file" in err and not out.exists()


def test_missing_rules_file(run_cli, write_file, tmp_path):
    a = write_file("a.csv", A)
    out = tmp_path / "o.csv"
    code, _, err = merge(run_cli, "--location", f"shop={a}", "--rules", str(tmp_path / "r.csv"), "--out", str(out))
    assert code == 2 and err.startswith("stockmerge: error:") and not out.exists()


def test_input_is_folder(run_cli, rules, tmp_path):
    d = tmp_path / "dir"
    d.mkdir()
    out = tmp_path / "o.csv"
    code, _, err = merge(run_cli, "--location", f"shop={d}", "--rules", rules, "--out", str(out))
    assert code == 2 and "Traceback" not in err and not out.exists()


# R2.2
def test_out_is_input(run_cli, write_file, rules):
    a = write_file("a.csv", A + "05/03/2026 10:00,X,1,each\n")
    before = open(a, "rb").read()
    code, _, err = merge(run_cli, "--location", f"shop={a}", "--rules", rules, "--out", a)
    assert code == 2 and "also an input file" in err
    assert open(a, "rb").read() == before


def test_out_missing_folder(run_cli, write_file, rules, tmp_path):
    a = write_file("a.csv", A)
    code, _, err = merge(run_cli, "--location", f"shop={a}", "--rules", rules,
                         "--out", str(tmp_path / "nope" / "o.csv"))
    assert code == 2 and "cannot write output" in err


def test_out_hard_link_to_input(run_cli, write_file, rules, tmp_path):
    a = write_file("a.csv", A)
    link = tmp_path / "link.csv"
    os.link(a, link)
    code, _, _ = merge(run_cli, "--location", f"shop={a}", "--rules", rules, "--out", str(link))
    assert code == 2


def test_out_is_rules(run_cli, write_file, rules):
    a = write_file("a.csv", A)
    code, _, _ = merge(run_cli, "--location", f"shop={a}", "--rules", rules, "--out", rules)
    assert code == 2


# R4.11
def test_zero_quantity_categorised(run_cli, write_file, tmp_path):
    a = write_file("a.csv", A + "05/03/2026 10:00,ABC,0,each\n")
    r = write_file("r.csv", "pattern,category\nab,Food\n")
    out = tmp_path / "o.csv"
    code, _, _ = merge(run_cli, "--location", f"shop={a}", "--rules", r, "--out", str(out))
    assert code == 0 and out.read_text() == HEADER + "shop,ABC,0,Food,\n"


# R5.1 + R4.7
def test_dedup_on_minute_time(run_cli, write_file, rules, tmp_path, read_out):
    a = write_file("a.csv", B + "2026-03-05T14:30:05,X,1,\n")
    b = write_file("b.csv", B + "2026-03-05T14:30:59,X,1,\n")
    out = str(tmp_path / "o.csv")
    code, _, err = merge(run_cli, "--location", f"shop={a}", "--location", f"shop={b}",
                         "--rules", rules, "--out", out)
    assert code == 0 and len(read_out(out)) == 1 and "removed 1 duplicates" in err


# R5.6
def test_dedup_before_moves(run_cli, write_file, rules, tmp_path, read_out):
    b1 = write_file("b1.csv", A + "05/03/2026 10:00,X,-1,each\n")
    b2 = write_file("b2.csv", B + "2026-03-05T10:00:10,X,-1,\n")
    s = write_file("s.csv", A + "05/03/2026 10:30,X,1,each\n")
    out = str(tmp_path / "o.csv")
    code, _, err = merge(run_cli, "--location", f"back={b1}", "--location", f"back={b2}",
                         "--location", f"shop={s}", "--rules", rules, "--out", out)
    rows = read_out(out)
    assert code == 0 and len(rows) == 2
    assert all(r["category"] == "Move" and r["move_id"] == "M0001" for r in rows)
    assert "removed 1 duplicates" in err and "linked 1 moves" in err


# R6.1 + R4.7, R6.3
def test_move_window_on_minute_times(run_cli, write_file, rules, tmp_path, read_out):
    b = write_file("b.csv", B + "2026-03-05T10:00:59,X,-1,\n")
    s = write_file("s.csv", B + "2026-03-05T12:00:30,X,1,\n")
    out = str(tmp_path / "o.csv")
    code, _, _ = merge(run_cli, "--location", f"back={b}", "--location", f"shop={s}",
                       "--rules", rules, "--out", out)
    rows = read_out(out)
    assert code == 0 and [r["category"] for r in rows] == ["Move", "Move"]
    assert rows[0]["move_id"] == rows[1]["move_id"] != ""


def test_move_rows_not_categorised(run_cli, write_file, tmp_path, read_out):
    b = write_file("b.csv", A + "05/03/2026 10:05,ABC,-6,each\n")
    s = write_file("s.csv", A + "05/03/2026 11:40,abc,6,each\n")
    r = write_file("r.csv", "pattern,category\nabc,Food\n")
    out = str(tmp_path / "o.csv")
    merge(run_cli, "--location", f"back={b}", "--location", f"shop={s}", "--rules", r, "--out", out)
    assert [(x["category"], x["move_id"]) for x in read_out(out)] == [("Move", "M0001")] * 2


# R7.1
def test_uncategorised(run_cli, write_file, rules, tmp_path, read_out):
    a = write_file("a.csv", A + "05/03/2026 10:00,ZZZ,1,each\n")
    out = str(tmp_path / "o.csv")
    merge(run_cli, "--location", f"shop={a}", "--rules", rules, "--out", out)
    row = read_out(out)[0]
    assert row["category"] == "Uncategorised" and row["move_id"] == ""


# R8.1, Worked example, Summary
def test_worked_example(run_cli, worked, tmp_path):
    out = tmp_path / "inv.csv"
    code, stdout, err = merge(run_cli, *worked, "--out", str(out))
    assert code == 0 and stdout == ""
    assert out.read_bytes() == WORKED_OUT.encode()
    assert err.rstrip("\n").splitlines()[-1] == WORKED_SUMMARY


# R9.1
def test_no_rows_writes_header(run_cli, write_file, rules, tmp_path):
    a = write_file("a.csv", A)
    out = tmp_path / "o.csv"
    code, _, err = merge(run_cli, "--location", f"shop={a}", "--rules", rules, "--out", str(out))
    assert code == 0 and out.read_bytes() == HEADER.encode() and "no valid rows" in err


# R9.2
def test_output_bytes(run_cli, write_file, rules, tmp_path):
    a = write_file("a.csv", A + "05/03/2026 10:00,X,-1,case\r\n")
    out = tmp_path / "o.csv"
    merge(run_cli, "--location", f"shop={a}", "--rules", rules, "--out", str(out))
    data = out.read_bytes()
    assert not data.startswith(b"\xef\xbb\xbf") and b"\r" not in data
    assert b"shop,X,-12,Uncategorised,\n" in data


# R9.3, CUJ 4
def test_failed_run_keeps_existing_out(run_cli, write_file, rules, tmp_path):
    bad = write_file("bad.csv", "foo,bar\n1,2\n")
    out = tmp_path / "inv.csv"
    out.write_bytes(b"yesterday\n")
    code, _, err = merge(run_cli, "--location", f"shop={bad}", "--rules", rules, "--out", str(out))
    assert code == 2 and "unrecognised header" in err
    assert out.read_bytes() == b"yesterday\n"


# G4, CUJ 5
def test_deterministic(run_cli, worked, tmp_path):
    o1, o2 = tmp_path / "1.csv", tmp_path / "2.csv"
    merge(run_cli, *worked, "--out", str(o1))
    merge(run_cli, *worked, "--out", str(o2))
    assert o1.read_bytes() == o2.read_bytes()


# G5 backstop
def test_backstop(monkeypatch, write_file, rules, tmp_path, capsys):
    a = write_file("a.csv", A)

    def boom(*a, **k):
        raise OSError("boom")

    monkeypatch.setattr("stockmerge.cli.dedup", boom)
    code = cli.main(["merge", "--location", f"shop={a}", "--rules", rules, "--out", str(tmp_path / "o.csv")])
    assert code == 2 and capsys.readouterr().err.splitlines()[-1].startswith("stockmerge: error:")


# CUJ 1
def test_cuj1(run_cli, write_file, rules, tmp_path, read_out):
    s1 = write_file("shop.csv", A + "05/03/2026 14:30,00123,1,case\n" * 2)
    s2 = write_file("shop2.csv", B + "2026-03-05T14:30:41,123,12,\n" * 3)
    out = str(tmp_path / "inv.csv")
    code, _, _ = merge(run_cli, "--location", f"shop floor={s1}", "--location", f"shop floor={s2}",
                       "--rules", rules, "--out", out)
    rows = read_out(out)
    assert code == 0
    assert [r["sku"] for r in rows] == ["00123", "00123", "123"]
    assert all(r["qty_each"] == "12" for r in rows)


# CUJ 3
def test_cuj3(run_cli, write_file, rules, tmp_path, read_out):
    a = write_file("a.csv", A + "05/03/2026 10:00,X,1,each\n31/02/2026 10:00,X,1,each\n05/03/2026 10:00,Y,2.5,each\n")
    out = str(tmp_path / "o.csv")
    code, _, err = merge(run_cli, "--location", f"shop={a}", "--rules", rules, "--out", out)
    assert code == 0 and len(read_out(out)) == 1
    assert f"stockmerge: warning: {a}:3: bad date" in err
    assert f"stockmerge: warning: {a}:4: quantity is not a whole number" in err
    assert "skipped 2 rows" in err
