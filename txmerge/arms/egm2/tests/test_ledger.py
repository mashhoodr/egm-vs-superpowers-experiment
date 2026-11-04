import datetime
import os
import stat
from decimal import Decimal

import pytest

from txmerge.ledger import format_amount, sort_rows, write_ledger
from txmerge.model import Row, TxmergeError

D = datetime.date(2026, 3, 1)


def row(account, arg, line, date=D, desc="X", amount="-1.00"):
    return Row(account, date, desc, Decimal(amount), arg, line)


def test_sort_order_tie_breaks():
    rows = [
        row("b", 0, 2),
        row("a", 1, 2),
        row("a", 0, 5),
        row("a", 0, 3),
        row("z", 0, 9, date=datetime.date(2026, 2, 28)),
    ]
    out = sort_rows(rows)
    assert [(r.account, r.arg_index, r.line_no) for r in out] == [
        ("z", 0, 9),
        ("a", 0, 3),
        ("a", 0, 5),
        ("a", 1, 2),
        ("b", 0, 2),
    ]


def test_format_amount():
    assert format_amount(Decimal("-0.00")) == "0.00"
    assert format_amount(Decimal("0.00")) == "0.00"
    assert format_amount(Decimal("-12.50")) == "-12.50"
    assert format_amount(Decimal("1250.00")) == "1250.00"


def test_written_bytes(tmp_path):
    path = str(tmp_path / "out.csv")
    rows = [row("cur", 0, 2, desc="SHOP, LONDON", amount="-12.50"), row("card", 1, 2, amount="3.00")]
    write_ledger(path, rows, ["Groceries", "Transfer"], ["", "T0001"])
    data = open(path, "rb").read()
    assert data == (
        b"date,account,description,amount,category,transfer_id\n"
        b'2026-03-01,cur,"SHOP, LONDON",-12.50,Groceries,\n'
        b"2026-03-01,card,X,3.00,Transfer,T0001\n"
    )
    assert b"\r" not in data
    assert not data.startswith(b"\xef\xbb\xbf")


def test_missing_directory_raises(tmp_path):
    with pytest.raises(TxmergeError, match="cannot write"):
        write_ledger(str(tmp_path / "nope" / "out.csv"), [], [], [])


def test_new_ledger_mode_0600(tmp_path):
    path = tmp_path / "out.csv"
    write_ledger(str(path), [], [], [])
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_existing_mode_kept(tmp_path):
    path = tmp_path / "out.csv"
    path.write_text("old")
    os.chmod(path, 0o644)
    write_ledger(str(path), [], [], [])
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o644
    assert path.read_text().startswith("date,")
    assert [p.name for p in tmp_path.iterdir()] == ["out.csv"]
