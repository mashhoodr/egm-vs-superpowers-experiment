import csv
from datetime import date
from decimal import Decimal

from txmerge.model import LedgerEntry, Transaction
from txmerge.writer import HEADER, format_amount, write_ledger


def entry(desc="X", amount="-12.5", cat="Food", tid=""):
    return LedgerEntry(Transaction("cur", date(2026, 1, 3), Decimal(amount), desc, (0, 2)), cat, tid)


def test_format_amount():
    assert format_amount(Decimal("-12.5")) == "-12.50"
    assert format_amount(Decimal("1250")) == "1250.00"
    assert format_amount(Decimal("-0.00")) == "0.00"
    assert format_amount(Decimal("0.005")) == "0.01"
    assert format_amount(Decimal("1E+3")) == "1000.00"


def test_writes_exact_header_and_rows(tmp_path):
    p = tmp_path / "out.csv"
    write_ledger(str(p), [entry(), entry(desc="SAV", amount="100", cat="Transfer", tid="T0001")])
    assert p.read_bytes() == (
        b"date,account,description,amount,category,transfer_id\n"
        b"2026-01-03,cur,X,-12.50,Food,\n"
        b"2026-01-03,cur,SAV,100.00,Transfer,T0001\n"
    )
    assert HEADER == ["date", "account", "description", "amount", "category", "transfer_id"]


def test_description_with_comma_and_quotes_round_trips(tmp_path):
    p = tmp_path / "out.csv"
    desc = 'SHOP, "BEST" LTD'
    write_ledger(str(p), [entry(desc=desc)])
    with open(p, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert rows[1][2] == desc


def test_failure_leaves_no_output_and_keeps_existing_file(tmp_path):
    import pytest
    out = tmp_path / "out.csv"
    out.write_text("old", encoding="utf-8")
    good = LedgerEntry(Transaction("a", date(2026, 1, 1), Decimal("1"), "X", (0, 2)), "C", "")
    bad = LedgerEntry(Transaction("a", date(2026, 1, 2), Decimal("1" + "0" * 40), "Y", (0, 3)), "C", "")
    with pytest.raises(ArithmeticError):
        write_ledger(str(out), [good, bad])
    assert out.read_text(encoding="utf-8") == "old"
    assert [p.name for p in tmp_path.iterdir()] == ["out.csv"]
