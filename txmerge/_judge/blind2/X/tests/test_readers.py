import datetime
from decimal import Decimal

import pytest

from txmerge.model import TxmergeError
from txmerge.readers import read_export

A_HEADER = "Date,Description,Debit,Credit,Balance\n"
B_HEADER = "Transaction Date,Posting Date,Details,Amount\n"


def write(tmp_path, text, name="in.csv", mode="w"):
    p = tmp_path / name
    if isinstance(text, bytes):
        p.write_bytes(text)
    else:
        p.write_text(text, encoding="utf-8")
    return str(p)


def read(path):
    return read_export(path, "acc", 0)


def test_format_a_debit_credit_thousands_and_dates(tmp_path):
    path = write(
        tmp_path,
        A_HEADER
        + "05/03/2026,SHOP,12.50,,100\n"
        + '5/3/2026,PAY,,"1,250.00",100\n',
    )
    rows, skipped = read(path)
    assert skipped == 0
    assert rows[0].amount == Decimal("-12.50")
    assert rows[0].date == datetime.date(2026, 3, 5)
    assert rows[1].amount == Decimal("1250.00")
    assert rows[1].date == datetime.date(2026, 3, 5)
    assert rows[1].line_no == 3


def test_format_b_signed_amounts_and_transaction_date(tmp_path):
    path = write(
        tmp_path,
        B_HEADER
        + "2026-03-05,garbage,CAFE,-12.50\n"
        + "2026-03-06,,REFUND,+3\n"
        + '2026-03-07,x,BIG,"1,250.00"\n',
    )
    rows, skipped = read(path)
    assert skipped == 0
    assert [r.amount for r in rows] == [Decimal("-12.50"), Decimal("3.00"), Decimal("1250.00")]
    assert str(rows[1].amount) == "3.00"
    assert rows[0].date == datetime.date(2026, 3, 5)


def test_balance_column_ignored(tmp_path):
    path = write(tmp_path, A_HEADER + "05/03/2026,SHOP,1.00,,not a number\n")
    rows, skipped = read(path)
    assert skipped == 0 and len(rows) == 1


def test_bom_and_spaces_around_header(tmp_path):
    text = " Date , Description,Debit ,Credit,Balance\n05/03/2026,X,1.00,,\n"
    path = write(tmp_path, b"\xef\xbb\xbf" + text.encode())
    rows, _ = read(path)
    assert len(rows) == 1


def test_lowercase_header_rejected(tmp_path):
    path = write(tmp_path, "date,description,debit,credit,balance\n")
    with pytest.raises(TxmergeError, match="unrecognised header"):
        read(path)


def test_zero_counts_as_blank(tmp_path):
    path = write(
        tmp_path,
        A_HEADER
        + "05/03/2026,A,0.00,25.00,\n"
        + "05/03/2026,B,0,0.00,\n"
        + "05/03/2026,C,0.00,0,\n",
    )
    rows, skipped = read(path)
    assert [r.amount for r in rows] == [Decimal("25.00")]
    assert skipped == 2


@pytest.mark.parametrize(
    "line, reason",
    [
        ("05/03/2026,X,,,", "Debit and Credit both blank"),
        ("05/03/2026,X,1.00,2.00,", "Debit and Credit both filled"),
        ("05/03/2026,X,£5.00,,", "bad amount '£5.00'"),
        ("05/03/2026,X,(5.00),,", "bad amount '(5.00)'"),
        ("05/03/2026,X,1.234,,", "bad amount '1.234'"),
        ('05/03/2026,X,"1,25.00",,', "bad amount '1,25.00'"),
        ("05/03/2026,X,NaN,,", "bad amount 'NaN'"),
        ("05/03/2026,X,1e3,,", "bad amount '1e3'"),
        ("05/03/2026,X,-5.00,,", "bad amount '-5.00'"),
        ("31/02/2026,X,5.00,,", "bad date '31/02/2026'"),
        ("05/03/2026,X,5.00,", "expected 5 cells, got 4"),
        ("05/03/2026,X,1,250.00,,", "expected 5 cells, got 6"),
    ],
)
def test_bad_rows_skipped_with_exact_warning(tmp_path, capsys, line, reason):
    path = write(tmp_path, A_HEADER + "\n" + line + "\n")
    rows, skipped = read(path)
    assert rows == [] and skipped == 1
    err = capsys.readouterr().err
    assert err == f"txmerge: warning: {path}:3: {reason}; row skipped\n"


def test_blank_lines_skipped_silently(tmp_path, capsys):
    path = write(tmp_path, A_HEADER + "\n,,,,\n   \n05/03/2026,X,1.00,,\n")
    rows, skipped = read(path)
    assert len(rows) == 1 and skipped == 0
    assert rows[0].line_no == 5
    assert capsys.readouterr().err == ""


@pytest.mark.parametrize(
    "content, match",
    [
        ("Foo,Bar\n", "unrecognised header: Foo,Bar"),
        ("Date,Description,Debit,Credit,Balance,\n", "unrecognised header"),
        ("", "file is empty"),
        ("\n  \n", "file is empty"),
        (b"Date,Description,Debit,Credit,Balance\n05/03/2026,\xff\xfe,1,,\n", "cannot read"),
    ],
)
def test_file_level_errors(tmp_path, content, match):
    path = write(tmp_path, content)
    with pytest.raises(TxmergeError, match=match):
        read(path)


def test_missing_file(tmp_path):
    with pytest.raises(TxmergeError, match="cannot read"):
        read(str(tmp_path / "nope.csv"))


def test_header_only(tmp_path):
    assert read(write(tmp_path, A_HEADER)) == ([], 0)
    assert read(write(tmp_path, B_HEADER, name="b.csv")) == ([], 0)


def test_huge_amount_is_bad_amount_not_crash(tmp_path, capsys):
    big = "1234567890123456789012345678901234567890.00"
    path = write(tmp_path, A_HEADER + f"05/03/2026,X,{big},,\n")
    rows, skipped = read(path)
    assert rows == [] and skipped == 1
    assert f"bad amount '{big}'" in capsys.readouterr().err


def test_data_cells_trimmed_and_date_type(tmp_path):
    path = write(tmp_path, A_HEADER + " 05/03/2026 ,  SHOP  , 12.50 ,,\n")
    rows, _ = read(path)
    assert rows[0].amount == Decimal("-12.50")
    assert rows[0].description == "SHOP"
    assert type(rows[0].date) is datetime.date


def test_inner_whitespace_kept(tmp_path):
    path = write(tmp_path, A_HEADER + "05/03/2026,COSTA  COFFEE,1.00,,\n")
    rows, _ = read(path)
    assert rows[0].description == "COSTA  COFFEE"


def test_check_order(tmp_path, capsys):
    path = write(
        tmp_path,
        A_HEADER + "99/99/2026,X,,,\n" + "05/03/2026,X,abc,,\n",
    )
    read(path)
    err = capsys.readouterr().err
    assert ":2: bad date '99/99/2026'" in err
    assert ":3: bad amount 'abc'" in err


@pytest.mark.parametrize(
    "line, reason",
    [
        ("05/03/2026,x,X,-1.00", "bad date '05/03/2026'"),
        ("2026-03-05,x,X,£5", "bad amount '£5'"),
        ("2026-03-05,x,X", "expected 4 cells, got 3"),
    ],
)
def test_format_b_bad_rows(tmp_path, capsys, line, reason):
    path = write(tmp_path, B_HEADER + line + "\n")
    rows, skipped = read(path)
    assert rows == [] and skipped == 1
    assert f"{path}:2: {reason}; row skipped" in capsys.readouterr().err


def test_huge_quoted_field_is_cannot_read(tmp_path):
    import csv

    big = "x" * (csv.field_size_limit() + 10)
    path = write(tmp_path, A_HEADER + f'05/03/2026,"{big}",1.00,,\n')
    with pytest.raises(TxmergeError, match="cannot read"):
        read(path)
