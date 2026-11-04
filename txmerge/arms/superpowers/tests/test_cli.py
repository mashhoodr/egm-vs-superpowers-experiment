import argparse
import subprocess
import sys
from pathlib import Path

import pytest

from txmerge.cli import main, parse_account

REPO = Path(__file__).resolve().parent.parent

CUR1 = ("Date,Description,Debit,Credit,Balance\n"
        "01/01/2026,COSTA COFFEE,3.50,,996.50\n"
        "01/01/2026,COSTA COFFEE,3.50,,993.00\n"
        "02/01/2026,TO SAVINGS,100.00,,893.00\n"
        "03/01/2026,TESCO STORES,\"1,250.00\",,0\n")
CUR2 = ("Date,Description,Debit,Credit,Balance\n"
        "01/01/2026,costa  coffee,3.50,,1.00\n"
        "03/01/2026,TESCO STORES,\"1,250.00\",,0\n"
        "05/01/2026,CARD PAYMENT,200.00,,0\n"
        "06/01/2026,BAD ROW,,,0\n")
SAV = ("Date,Description,Debit,Credit,Balance\n"
       "03/01/2026,FROM CURRENT,,100.00,100.00\n")
CARD = ("Transaction Date,Posting Date,Details,Amount\n"
        "2026-01-04,2026-01-06,AMAZON MKTPLACE,-20.00\n"
        "2026-01-07,2026-01-08,PAYMENT RECEIVED,200.00\n")
RULES = "pattern,category\ncosta,Eating Out\ntesco,Groceries\namazon,Shopping\n"

EXPECTED = (
    "date,account,description,amount,category,transfer_id\n"
    "2026-01-01,cur,COSTA COFFEE,-3.50,Eating Out,\n"
    "2026-01-01,cur,COSTA COFFEE,-3.50,Eating Out,\n"
    "2026-01-02,cur,TO SAVINGS,-100.00,Transfer,T0001\n"
    "2026-01-03,cur,TESCO STORES,-1250.00,Groceries,\n"
    "2026-01-03,sav,FROM CURRENT,100.00,Transfer,T0001\n"
    "2026-01-04,card,AMAZON MKTPLACE,-20.00,Shopping,\n"
    "2026-01-05,cur,CARD PAYMENT,-200.00,Transfer,T0002\n"
    "2026-01-07,card,PAYMENT RECEIVED,200.00,Transfer,T0002\n"
)


@pytest.fixture
def files(tmp_path):
    for name, text in [("cur1.csv", CUR1), ("cur2.csv", CUR2), ("sav.csv", SAV),
                       ("card.csv", CARD), ("rules.csv", RULES)]:
        (tmp_path / name).write_text(text, encoding="utf-8")
    return tmp_path


def args(d, out="out.csv"):
    return ["merge",
            "--account", f"cur={d / 'cur1.csv'}", "--account", f"cur={d / 'cur2.csv'}",
            "--account", f"sav={d / 'sav.csv'}", "--account", f"card={d / 'card.csv'}",
            "--rules", str(d / "rules.csv"), "--out", str(d / out)]


def test_parse_account_splits_on_first_equals():
    assert parse_account("cur=/tmp/a=b.csv") == ("cur", "/tmp/a=b.csv")
    for bad in ["cur", "=x.csv", "cur="]:
        with pytest.raises(argparse.ArgumentTypeError):
            parse_account(bad)


def test_end_to_end(files, capsys):
    assert main(args(files)) == 0
    assert (files / "out.csv").read_text(encoding="utf-8") == EXPECTED
    err = capsys.readouterr().err
    assert f"WARNING: {files / 'cur2.csv'}:5:" in err


def test_rerun_is_byte_identical(files):
    assert main(args(files, "a.csv")) == 0
    assert main(args(files, "b.csv")) == 0
    assert (files / "a.csv").read_bytes() == (files / "b.csv").read_bytes()


def test_unknown_header_exits_2_and_writes_nothing(files, capsys):
    (files / "sav.csv").write_text("foo,bar\n1,2\n", encoding="utf-8")
    assert main(args(files)) == 2
    assert not (files / "out.csv").exists()
    assert "sav.csv" in capsys.readouterr().err


def test_missing_input_exits_2_and_writes_nothing(files):
    (files / "card.csv").unlink()
    assert main(args(files)) == 2
    assert not (files / "out.csv").exists()


def test_missing_rules_exits_2(files):
    (files / "rules.csv").unlink()
    assert main(args(files)) == 2
    assert not (files / "out.csv").exists()


def test_unwritable_out_exits_2(files):
    assert main(args(files, "no/such/dir/out.csv")) == 2


def test_bad_account_arg_exits_2(files):
    with pytest.raises(SystemExit) as exc:
        main(["merge", "--account", "cur", "--rules", str(files / "rules.csv"),
              "--out", str(files / "o.csv")])
    assert exc.value.code == 2


def test_python_dash_m_entry_point(files):
    proc = subprocess.run([sys.executable, "-m", "txmerge", *args(files)],
                          cwd=REPO, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert (files / "out.csv").read_text(encoding="utf-8") == EXPECTED


def test_huge_amount_exits_2_and_writes_nothing(files, capsys):
    (files / "cur1.csv").write_text(
        "Date,Description,Debit,Credit,Balance\n01/01/2026,BIG,1" + "0" * 40 + ",,0\n",
        encoding="utf-8")
    assert main(args(files)) == 2
    assert "error:" in capsys.readouterr().err
    assert not (files / "out.csv").exists()
    assert [p.name for p in files.iterdir() if p.name.startswith("out")] == []
