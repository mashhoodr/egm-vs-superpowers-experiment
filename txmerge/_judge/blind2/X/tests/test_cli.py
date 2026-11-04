import os
import subprocess
import sys
from pathlib import Path

import pytest

from txmerge import cli
from txmerge.cli import main, parse_account

ROOT = Path(__file__).resolve().parents[1]
A_HEADER = "Date,Description,Debit,Credit,Balance\n"
B_HEADER = "Transaction Date,Posting Date,Details,Amount\n"


def put(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def merge_args(accounts, rules, out):
    args = ["merge"]
    for name, path in accounts:
        args += ["--account", f"{name}={path}"]
    return args + ["--rules", rules, "--out", out]


@pytest.fixture
def scenario(tmp_path):
    """Two overlapping current-account exports, one card export, rules."""
    jan = put(
        tmp_path,
        "cur_jan.csv",
        A_HEADER
        + "08/01/2026,SALARY,,2000.00,\n"
        + "10/01/2026,TESCO STORES,12.50,,\n"
        + "10/01/2026,COFFEE,3.50,,\n"
        + "10/01/2026,COFFEE,3.50,,\n"
        + "15/01/2026,CARD PAYMENT,500.00,,\n",
    )
    feb = put(
        tmp_path,
        "cur_feb.csv",
        A_HEADER
        + "10/01/2026,tesco  stores,12.50,,\n"
        + "10/01/2026,COFFEE,3.50,,\n"
        + "15/01/2026,CARD PAYMENT,500.00,,\n"
        + '20/01/2026,"RENT, FLAT",\"1,250.00\",,\n',
    )
    card = put(
        tmp_path,
        "card.csv",
        B_HEADER
        + "2026-01-12,2026-01-13,AMAZON,-40.00\n"
        + "2026-01-17,2026-01-18,PAYMENT RECEIVED,500.00\n",
    )
    rules = put(tmp_path, "rules.csv", "pattern,category\nTESCO,Groceries\nrent,Housing\n")
    out = str(tmp_path / "ledger.csv")
    accounts = [("current", jan), ("current", feb), ("card", card)]
    return merge_args(accounts, rules, out), out


EXPECTED = (
    "date,account,description,amount,category,transfer_id\n"
    "2026-01-08,current,SALARY,2000.00,Uncategorised,\n"
    "2026-01-10,current,TESCO STORES,-12.50,Groceries,\n"
    "2026-01-10,current,COFFEE,-3.50,Uncategorised,\n"
    "2026-01-10,current,COFFEE,-3.50,Uncategorised,\n"
    "2026-01-12,card,AMAZON,-40.00,Uncategorised,\n"
    "2026-01-15,current,CARD PAYMENT,-500.00,Transfer,T0001\n"
    "2026-01-17,card,PAYMENT RECEIVED,500.00,Transfer,T0001\n"
    '2026-01-20,current,"RENT, FLAT",-1250.00,Housing,\n'
)


def test_cuj1_overlap_and_exact_bytes(scenario, capsys):
    args, out = scenario
    assert main(args) == 0
    assert open(out, "rb").read() == EXPECTED.encode()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "txmerge: 11 rows read, 0 skipped, 3 duplicates removed, "
        "1 transfers linked, 8 rows written\n"
    )


def test_cuj2_card_payment_is_transfer(tmp_path):
    cur = put(tmp_path, "cur.csv", A_HEADER + "05/03/2026, CARD PAYMENT, 500.00,,\n")
    card = put(tmp_path, "card.csv", B_HEADER + "2026-03-07,2026-03-08,PAYMENT RECEIVED,500.00\n")
    rules = put(tmp_path, "rules.csv", "pattern,category\npayment,Bills\n")
    out = str(tmp_path / "out.csv")
    assert main(merge_args([("current", cur), ("card", card)], rules, out)) == 0
    lines = open(out).read().splitlines()[1:]
    assert lines == [
        "2026-03-05,current,CARD PAYMENT,-500.00,Transfer,T0001",
        "2026-03-07,card,PAYMENT RECEIVED,500.00,Transfer,T0001",
    ]


def test_cuj3_rerun_byte_identical(scenario):
    args, out = scenario
    assert main(args) == 0
    first = open(out, "rb").read()
    assert main(args) == 0
    assert open(out, "rb").read() == first


def test_cuj4_unknown_format(scenario, tmp_path, capsys):
    args, out = scenario
    bad = put(tmp_path, "bad.csv", "Foo,Bar\n1,2\n")
    args = ["merge", "--account", f"x={bad}"] + args[1:]
    assert main(args) == 2
    err = capsys.readouterr().err
    assert err == f"txmerge: error: {bad}: unrecognised header: Foo,Bar\n"
    assert not os.path.exists(out)


def test_cuj4_existing_ledger_unchanged(tmp_path):
    bad = put(tmp_path, "bad.csv", "Foo,Bar\n")
    rules = put(tmp_path, "rules.csv", "pattern,category\n")
    out = put(tmp_path, "out.csv", "old ledger\n")
    assert main(merge_args([("x", bad)], rules, out)) == 2
    assert open(out).read() == "old ledger\n"


def test_cuj5_bad_row(tmp_path, capsys):
    lines = [A_HEADER] + [f"0{d}/03/2026,SHOP{d},1.00,,\n" for d in range(1, 6)]
    lines.append("07/03/2026,BROKEN,,,\n")  # line 7
    cur = put(tmp_path, "cur.csv", "".join(lines))
    rules = put(tmp_path, "rules.csv", "pattern,category\n")
    out = str(tmp_path / "out.csv")
    assert main(merge_args([("cur", cur)], rules, out)) == 0
    assert "BROKEN" not in open(out).read()
    err = capsys.readouterr().err
    assert f"txmerge: warning: {cur}:7: Debit and Credit both blank; row skipped\n" in err
    assert "6 rows read, 1 skipped, 0 duplicates removed, 0 transfers linked, 5 rows written" in err


def test_two_names_one_file_self_pair(tmp_path):
    f = put(tmp_path, "f.csv", A_HEADER + "01/03/2026,OUT,50.00,,\n01/03/2026,IN,,50.00,\n")
    rules = put(tmp_path, "rules.csv", "pattern,category\n")
    out = str(tmp_path / "out.csv")
    assert main(merge_args([("a", f), ("b", f)], rules, out)) == 0
    body = open(out).read().splitlines()[1:]
    assert len(body) == 4
    assert all(line.endswith(",Transfer,T0001") or line.endswith(",Transfer,T0002") for line in body)


def test_zero_amount_row(tmp_path):
    card = put(tmp_path, "card.csv", B_HEADER + "2026-03-01,,FEE WAIVED,0.00\n")
    card2 = put(tmp_path, "card2.csv", B_HEADER + "2026-03-01,,ZERO,-0.00\n")
    rules = put(tmp_path, "rules.csv", "pattern,category\nfee,Fees\n")
    out = str(tmp_path / "out.csv")
    assert main(merge_args([("card", card), ("other", card2)], rules, out)) == 0
    assert open(out).read().splitlines()[1:] == [
        "2026-03-01,card,FEE WAIVED,0.00,Fees,",
        "2026-03-01,other,ZERO,0.00,Uncategorised,",
    ]


def test_existing_out_overwritten(scenario):
    args, out = scenario
    with open(out, "w") as f:
        f.write("stale\n")
    assert main(args) == 0
    assert open(out, "rb").read() == EXPECTED.encode()


def test_out_equal_to_input(tmp_path, capsys):
    cur = put(tmp_path, "cur.csv", A_HEADER + "01/03/2026,X,1.00,,\n")
    rules = put(tmp_path, "rules.csv", "pattern,category\n")
    before = open(cur, "rb").read()
    assert main(merge_args([("cur", cur)], rules, cur)) == 2
    assert open(cur, "rb").read() == before
    assert capsys.readouterr().err.endswith(f"txmerge: error: {cur}: --out is also an input\n")


def test_out_equal_to_rules(tmp_path):
    cur = put(tmp_path, "cur.csv", A_HEADER + "01/03/2026,X,1.00,,\n")
    rules = put(tmp_path, "rules.csv", "pattern,category\n")
    assert main(merge_args([("cur", cur)], rules, rules)) == 2
    assert open(rules).read() == "pattern,category\n"


def test_samefile_oserror(tmp_path, monkeypatch, capsys):
    cur = put(tmp_path, "cur.csv", A_HEADER)
    rules = put(tmp_path, "rules.csv", "pattern,category\n")
    out = put(tmp_path, "out.csv", "old\n")

    def boom(a, b):
        raise OSError("nope")

    monkeypatch.setattr(cli.os.path, "samefile", boom)
    assert main(merge_args([("cur", cur)], rules, out)) == 2
    assert f"txmerge: error: cannot read {cur}: nope" in capsys.readouterr().err
    assert open(out).read() == "old\n"


@pytest.mark.parametrize(
    "rules_text, message",
    [(None, "cannot read"), ("", "file is empty"), ("a,b\n", "header must be pattern,category")],
)
def test_bad_rules_file(tmp_path, capsys, rules_text, message):
    cur = put(tmp_path, "cur.csv", A_HEADER)
    rules = str(tmp_path / "rules.csv")
    if rules_text is not None:
        put(tmp_path, "rules.csv", rules_text)
    out = str(tmp_path / "out.csv")
    assert main(merge_args([("cur", cur)], rules, out)) == 2
    assert message in capsys.readouterr().err
    assert not os.path.exists(out)


@pytest.mark.parametrize(
    "argv",
    [
        ["merge", "--account", "a=x.csv", "--out", "o.csv"],
        ["merge", "--account", "a=x.csv", "--rules", "r.csv"],
        ["merge", "--rules", "r.csv", "--out", "o.csv"],
        ["--account", "a=x.csv", "--rules", "r.csv", "--out", "o.csv"],
        [],
    ],
)
def test_usage_errors(argv):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2


@pytest.mark.parametrize("value", ["noequals", "=path", "name=", " = "])
def test_bad_account_value(value, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["merge", "--account", value, "--rules", "r.csv", "--out", "o.csv"])
    assert exc.value.code == 2
    assert f"--account must be NAME=PATH, got '{value}'" in capsys.readouterr().err


def test_parse_account():
    assert parse_account("a=b=c") == ("a", "b=c")
    assert parse_account(" cur = x.csv ") == ("cur", "x.csv")


@pytest.mark.parametrize("existing", [False, True])
def test_failing_write(scenario, monkeypatch, capsys, existing):
    args, out = scenario
    if existing:
        with open(out, "wb") as f:
            f.write(b"old ledger\n")

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr("txmerge.ledger.os.replace", boom)
    assert main(args) == 2
    assert f"txmerge: error: cannot write {out}: disk full" in capsys.readouterr().err
    if existing:
        assert open(out, "rb").read() == b"old ledger\n"
    else:
        assert not os.path.exists(out)
    assert not list(Path(out).parent.glob(".txmerge-*.tmp"))


def test_subprocess_entry_point(scenario):
    args, out = scenario
    result = subprocess.run(
        [sys.executable, "-m", "txmerge", *args], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0
    assert result.stdout == ""
    assert "1 transfers linked" in result.stderr
    assert open(out, "rb").read() == EXPECTED.encode()
