from datetime import date
from decimal import Decimal

import pytest

from txmerge.model import InputError, Transaction
from txmerge.readers import parse_amount, read_export


def write(tmp_path, name, text, newline="\n"):
    p = tmp_path / name
    p.write_bytes(text.replace("\n", newline).encode("utf-8"))
    return str(p)


def collect():
    msgs = []
    return msgs, msgs.append


def test_format_a_debit_and_credit(tmp_path):
    path = write(tmp_path, "a.csv",
                 "Date,Description,Debit,Credit,Balance\n"
                 "03/01/2026,TESCO STORE,12.50,,100.00\n"
                 "04/01/2026,SALARY,,2000.00,2100.00\n")
    msgs, warn = collect()
    rows = read_export("cur", path, 0, warn)
    assert rows == [
        Transaction("cur", date(2026, 1, 3), Decimal("-12.50"), "TESCO STORE", (0, 2)),
        Transaction("cur", date(2026, 1, 4), Decimal("2000.00"), "SALARY", (0, 3)),
    ]
    assert msgs == []


def test_format_a_thousands_and_no_decimals(tmp_path):
    path = write(tmp_path, "a.csv",
                 'Date,Description,Debit,Credit,Balance\n'
                 '05/01/2026,RENT,"1,250",,0\n'
                 '06/01/2026,BONUS,,"1,250.5",0\n')
    rows = read_export("cur", path, 0, lambda m: None)
    assert [r.amount for r in rows] == [Decimal("-1250"), Decimal("1250.5")]


def test_format_b_uses_transaction_date_and_signed_amount(tmp_path):
    path = write(tmp_path, "b.csv",
                 "Transaction Date,Posting Date,Details,Amount\n"
                 "2026-01-03,2026-01-05,  AMAZON  ,-30.00\n"
                 "2026-01-04,2026-01-06,PAYMENT RECEIVED,500.00\n")
    rows = read_export("card", path, 1, lambda m: None)
    assert rows == [
        Transaction("card", date(2026, 1, 3), Decimal("-30.00"), "AMAZON", (1, 2)),
        Transaction("card", date(2026, 1, 4), Decimal("500.00"), "PAYMENT RECEIVED", (1, 3)),
    ]


def test_header_with_bom_crlf_and_spaces(tmp_path):
    p = tmp_path / "a.csv"
    p.write_bytes("﻿Date , Description,Debit,Credit,Balance \r\n"
                  "03/01/2026,X,1.00,,0\r\n".encode("utf-8"))
    rows = read_export("cur", str(p), 0, lambda m: None)
    assert len(rows) == 1 and rows[0].amount == Decimal("-1.00")


def test_unknown_header_raises(tmp_path):
    path = write(tmp_path, "x.csv", "foo,bar\n1,2\n")
    with pytest.raises(InputError):
        read_export("cur", path, 0, lambda m: None)


def test_empty_file_raises(tmp_path):
    path = write(tmp_path, "x.csv", "")
    with pytest.raises(InputError):
        read_export("cur", path, 0, lambda m: None)


def test_missing_file_raises(tmp_path):
    with pytest.raises(InputError):
        read_export("cur", str(tmp_path / "nope.csv"), 0, lambda m: None)


@pytest.mark.parametrize("line,reason", [
    ("03/01/2026,X,,,0", "neither"),
    ("03/01/2026,X,1.00,2.00,0", "both"),
    ("2026-01-03,X,1.00,,0", "date"),
    ("03/01/2026,X,abc,,0", "amount"),
    ("03/01/2026,X,-5.00,,0", "amount"),
    ("03/01/2026,X", "fields"),
])
def test_format_a_bad_rows_warn_and_skip(tmp_path, line, reason):
    path = write(tmp_path, "a.csv",
                 "Date,Description,Debit,Credit,Balance\n" + line + "\n"
                 "04/01/2026,OK,1.00,,0\n")
    msgs, warn = collect()
    rows = read_export("cur", path, 0, warn)
    assert [r.description for r in rows] == ["OK"]
    assert len(msgs) == 1
    assert msgs[0].startswith(f"WARNING: {path}:2:")
    assert reason in msgs[0]


def test_format_b_bad_rows_warn_and_skip(tmp_path):
    path = write(tmp_path, "b.csv",
                 "Transaction Date,Posting Date,Details,Amount\n"
                 "03/01/2026,2026-01-05,X,-1.00\n"
                 "2026-01-03,2026-01-05,Y,\n"
                 "2026-01-04,2026-01-05,OK,-2.00\n")
    msgs, warn = collect()
    rows = read_export("card", path, 0, warn)
    assert [r.description for r in rows] == ["OK"]
    assert len(msgs) == 2
    assert msgs[0].startswith(f"WARNING: {path}:2:") and "date" in msgs[0]
    assert msgs[1].startswith(f"WARNING: {path}:3:") and "amount" in msgs[1]


def test_blank_lines_ignored_silently(tmp_path):
    path = write(tmp_path, "a.csv",
                 "Date,Description,Debit,Credit,Balance\n\n"
                 "03/01/2026,X,1.00,,0\n,,,,\n")
    msgs, warn = collect()
    rows = read_export("cur", path, 0, warn)
    assert len(rows) == 1 and rows[0].source == (0, 3)
    assert msgs == []


def test_parse_amount():
    assert parse_amount(" 1,234.56 ") == Decimal("1234.56")
    with pytest.raises(ValueError):
        parse_amount("")
    with pytest.raises(ValueError):
        parse_amount("NaN")


# --- final-review fixes ---

def test_unclosed_quote_skips_only_that_line(tmp_path):
    path = write(tmp_path, "a.csv",
                 'Date,Description,Debit,Credit,Balance\n'
                 '01/01/2026,"ABC,3.50,,1\n'
                 '02/01/2026,TESCO,5.00,,1\n'
                 '03/01/2026,SHELL,6.00,,1\n'
                 '04/01/2026,"PAY",,2000.00,1\n'
                 '05/01/2026,AMAZON,7.00,,1\n')
    msgs, warn = collect()
    rows = read_export("cur", path, 0, warn)
    assert [(r.date, r.amount, r.description, r.source) for r in rows] == [
        (date(2026, 1, 2), Decimal("-5.00"), "TESCO", (0, 3)),
        (date(2026, 1, 3), Decimal("-6.00"), "SHELL", (0, 4)),
        (date(2026, 1, 4), Decimal("2000.00"), "PAY", (0, 5)),
        (date(2026, 1, 5), Decimal("-7.00"), "AMAZON", (0, 6)),
    ]
    assert len(msgs) == 1 and f"{path}:2:" in msgs[0] and "malformed CSV" in msgs[0]


def test_oversized_field_is_a_bad_row(tmp_path):
    path = write(tmp_path, "a.csv",
                 'Date,Description,Debit,Credit,Balance\n'
                 '01/01/2026,' + "x" * 200000 + ',1.00,,1\n'
                 '02/01/2026,OK,2.00,,1\n')
    msgs, warn = collect()
    rows = read_export("cur", path, 0, warn)
    assert [r.description for r in rows] == ["OK"]
    assert len(msgs) == 1 and ":2:" in msgs[0]


def test_malformed_header_is_input_error(tmp_path):
    path = write(tmp_path, "a.csv", 'Date,"Description\n01/01/2026,X,1,,1\n')
    with pytest.raises(InputError):
        read_export("cur", path, 0, lambda m: None)


@pytest.mark.parametrize("text", ["1e2", "1E5", "0x10", "1_000", "1e30", "+", ".", "1 2", ""])
def test_parse_amount_rejects_non_plain_numbers(text):
    with pytest.raises(ValueError):
        parse_amount(text)


@pytest.mark.parametrize("text,expected", [("12.50", "12.50"), ("+3", "3"), ("-.5", "-0.5"),
                                           ("5.", "5"), ("1,250", "1250"), (" 7 ", "7")])
def test_parse_amount_accepts_plain_numbers(text, expected):
    assert parse_amount(text) == Decimal(expected)


def test_exponent_amount_row_warned_and_skipped(tmp_path):
    path = write(tmp_path, "a.csv",
                 'Date,Description,Debit,Credit,Balance\n'
                 '01/01/2026,BAD,1e5,,1\n'
                 '02/01/2026,OK,2.00,,1\n')
    msgs, warn = collect()
    rows = read_export("cur", path, 0, warn)
    assert [r.description for r in rows] == ["OK"]
    assert len(msgs) == 1 and ":2:" in msgs[0]


def _a_amounts(tmp_path, debit, credit):
    path = write(tmp_path, "a.csv",
                 'Date,Description,Debit,Credit,Balance\n'
                 f'01/01/2026,X,{debit},{credit},1\n')
    msgs, warn = collect()
    return [r.amount for r in read_export("cur", path, 0, warn)], msgs


def test_zero_in_unused_credit_column(tmp_path):
    assert _a_amounts(tmp_path, "12.50", "0.00") == ([Decimal("-12.50")], [])


def test_zero_in_unused_debit_column(tmp_path):
    assert _a_amounts(tmp_path, "0.00", "5") == ([Decimal("5")], [])


def test_both_zero_keeps_zero_row(tmp_path):
    amounts, msgs = _a_amounts(tmp_path, "0.00", "0.00")
    assert amounts == [Decimal("0.00")] and msgs == []


def test_one_zero_other_blank_keeps_zero_row(tmp_path):
    amounts, msgs = _a_amounts(tmp_path, "", "0.00")
    assert amounts == [Decimal("0.00")] and msgs == []


def test_both_blank_still_skipped(tmp_path):
    amounts, msgs = _a_amounts(tmp_path, "", "")
    assert amounts == [] and "neither" in msgs[0]


def test_both_nonzero_still_skipped(tmp_path):
    amounts, msgs = _a_amounts(tmp_path, "1.00", "2.00")
    assert amounts == [] and "both" in msgs[0]


def test_negative_with_zero_other_still_bad(tmp_path):
    amounts, msgs = _a_amounts(tmp_path, "-5.00", "0.00")
    assert amounts == [] and len(msgs) == 1
