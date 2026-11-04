from datetime import date
from decimal import Decimal

import pytest

from txmerge.formats import (
    detect,
    parse_a,
    parse_amount,
    parse_b,
    read_export,
)
from txmerge.model import MalformedRow, TxmergeError, normalise

A_HEADER = "Date,Description,Debit,Credit,Balance\n"
B_HEADER = "Transaction Date,Posting Date,Details,Amount\n"


def collect():
    msgs = []
    return msgs, msgs.append


@pytest.mark.parametrize(
    "cells, amount",
    [
        (["01/02/2026", "Shop", "12.50", "", ""], Decimal("-12.50")),
        (["01/02/2026", "Shop", "", "12.50", ""], Decimal("12.50")),
        (["01/02/2026", "Shop", "1,250.00", "", ""], Decimal("-1250.00")),
    ],
)
def test_format_a_amounts(cells, amount):
    d, desc, a = parse_a(cells)
    assert (d, desc, a) == (date(2026, 2, 1), "Shop", amount)
    assert str(a) == str(amount)


def test_format_a_quoted_thousands_in_file(write):
    p = write("a.csv", A_HEADER + '01/02/2026,Rent,"1,250.00",,\n')
    records, skipped = read_export(0, "Cur", p, lambda m: None)
    assert skipped == 0
    assert records[0].amount == Decimal("-1250.00")


@pytest.mark.parametrize(
    "debit, credit, reason",
    [
        ("1.00", "2.00", "both Debit and Credit are filled"),
        ("", " ", "neither Debit nor Credit is filled"),
    ],
)
def test_format_a_filled_rules(debit, credit, reason):
    with pytest.raises(MalformedRow) as e:
        parse_a(["01/02/2026", "X", debit, credit, ""])
    assert str(e.value) == reason


@pytest.mark.parametrize("balance", ["abc", ""])
def test_format_a_balance_ignored(balance):
    # D4
    assert parse_a(["01/02/2026", "X", "1.00", "", balance])[2] == Decimal("-1.00")


@pytest.mark.parametrize(
    "text, expected",
    [("-1,250.00", "-1250.00"), ("+5.00", "5.00"), ("-0.00", "0.00")],
)
def test_format_b_signed_amounts(text, expected):
    # D5
    _, _, a = parse_b(["2026-02-01", "xyz", "Card", text])
    assert str(a) == expected


@pytest.mark.parametrize("text", ["+5.00", "-5.00"])
def test_format_a_rejects_signs(text):
    # D5
    with pytest.raises(MalformedRow) as e:
        parse_a(["01/02/2026", "X", text, "", ""])
    assert str(e.value) == f"invalid amount '{text}'"


@pytest.mark.parametrize("text", ["01/02/2026", "1/2/2026"])
def test_format_a_dates_accepted(text):
    # D6
    assert parse_a([text, "X", "1", "", ""])[0] == date(2026, 2, 1)


@pytest.mark.parametrize("text", ["2026-01-02", "2026-1-2"])
def test_format_b_dates_accepted(text):
    # D6
    assert parse_b([text, "", "X", "1"])[0] == date(2026, 1, 2)


@pytest.mark.parametrize(
    "text", ["31/02/2026", "2026/02/01", "02/01/26", "٠١/٠٢/٢٠٢٦"]
)
def test_format_a_dates_rejected(text):
    with pytest.raises(MalformedRow) as e:
        parse_a([text, "X", "1", "", ""])
    assert str(e.value) == f"invalid date '{text}'"


@pytest.mark.parametrize("text", ["2026-02-30", "01/02/2026"])
def test_format_b_dates_rejected(text):
    with pytest.raises(MalformedRow) as e:
        parse_b([text, "", "X", "1"])
    assert str(e.value) == f"invalid date '{text}'"


@pytest.mark.parametrize(
    "text",
    ["NaN", "1e3", "1,2,3", "12.345", "£5.00", ".50", "1250.", "١٢", "9" * 40],
)
def test_amounts_rejected(text):
    # D23
    with pytest.raises(MalformedRow) as e:
        parse_amount(f"  {text} ", signed=True)
    assert str(e.value) == f"invalid amount '{text}'"


def test_zero_debit_is_positive_zero():
    # D7
    a = parse_a(["01/02/2026", "X", "0.00", "", ""])[2]
    assert str(a) == "0.00"


def test_empty_description_accepted():
    # D22
    assert parse_b(["2026-01-02", "", "  ", "-1"])[1] == ""


def test_bom_and_padded_header(write):
    # D11
    p = write("a.csv", "﻿ Date , Description,Debit ,Credit,Balance\n01/02/2026,X,1,,\n")
    records, skipped = read_export(0, "Cur", p, lambda m: None)
    assert len(records) == 1 and skipped == 0


def test_only_blank_rows_is_empty_file(write):
    p = write("a.csv", "\n , ,\n\n")
    with pytest.raises(TxmergeError) as e:
        read_export(0, "Cur", p, lambda m: None)
    assert "unrecognised header (empty file)" in str(e.value)


def test_detect_unknown_header():
    with pytest.raises(TxmergeError) as e:
        detect(["a", "b"], "f.csv")
    assert str(e.value).startswith('f.csv: unrecognised header "a,b"; expected')


def test_blank_line_counts_in_line_number(write):
    # D11
    p = write("a.csv", A_HEADER + "\n01/13/2026,X,1,,\n")
    msgs, warn = collect()
    read_export(0, "Cur", p, warn)
    assert msgs == [f"{p}:3: invalid date '01/13/2026'"]


def test_multiline_row_reports_start_line(write):
    content = (
        A_HEADER
        + "01/02/2026,Ok,1,,\n"
        + '31/02/2026,"two\nlines",1,,\n'
        + "02/02/2026,Ok2,1,,\n"
        + "bad,X,1,,\n"
    )
    p = write("a.csv", content)
    msgs, warn = collect()
    records, skipped = read_export(0, "Cur", p, warn)
    assert msgs == [
        f"{p}:3: invalid date '31/02/2026'",
        f"{p}:6: invalid date 'bad'",
    ]
    assert skipped == 2
    assert [r.line for r in records] == [2, 5]


def test_quoted_comma_is_one_cell(write):
    # D11
    p = write("a.csv", A_HEADER + '01/02/2026,"Shop, Ltd",1,,\n')
    records, _ = read_export(0, "Cur", p, lambda m: None)
    assert records[0].description == "Shop, Ltd"


def test_header_only_gives_no_records(write):
    p = write("b.csv", B_HEADER)
    assert read_export(0, "Card", p, lambda m: None) == ([], 0)


def test_unquoted_thousands_extra_field(write):
    p = write("a.csv", A_HEADER + "01/02/2026,Rent,1,250.00,,\n")
    msgs, warn = collect()
    records, skipped = read_export(0, "Cur", p, warn)
    assert records == [] and skipped == 1
    assert msgs == [f"{p}:2: expected 5 fields, found 6"]


def test_reason_precedence_date_first():
    with pytest.raises(MalformedRow) as e:
        parse_a(["31/02/2026", "X", "1", "2", ""])
    assert str(e.value) == "invalid date '31/02/2026'"


def test_normalise():
    # D26
    assert normalise("  Coffee\t\tSHOP   x ") == "coffee shop x"
    assert normalise("STRASSE") == normalise("straße")
