from datetime import datetime

import pytest

from stockmerge.model import StockmergeError, Warnings
from stockmerge.readers import read_export

A = "Scanned At,SKU,Qty,Unit\n"
B = "timestamp,barcode,count,note\n"


@pytest.fixture
def read(write_file):
    def _read(content, name="e.csv"):
        path = write_file(name, content)
        w = Warnings()
        scans, n, s = read_export(0, "shop", path, w)
        return scans, n, s, w.messages, path

    return _read


# R4.1
def test_bom_file(read):
    scans, *_ = read(("﻿" + A + "05/03/2026 10:00,X,1,each\n").encode("utf-8"))
    assert len(scans) == 1


def test_crlf_file(read):
    scans, *_ = read(A.replace("\n", "\r\n") + "05/03/2026 10:00,X,1,each\r\n")
    assert len(scans) == 1 and scans[0].sku == "X"


def test_bad_byte_in_sku_skipped(read):
    data = A.encode() + b"05/03/2026 10:00,X\xff,1,each\n05/03/2026 10:00,Y,1,each\n"
    scans, n, s, msgs, path = read(data)
    assert [x.sku for x in scans] == ["Y"]
    assert msgs == [f"{path}:2: not valid UTF-8"]
    assert (n, s) == (2, 1)


def test_bad_byte_in_b_note_kept(read):
    scans, *_ = read(B.encode() + b"2026-03-05T10:00:00,X,1,caf\xff\n")
    assert len(scans) == 1


def test_bad_byte_in_header_is_unrecognised(read):
    with pytest.raises(StockmergeError, match="unrecognised header"):
        read(b"Scanned At,SKU\xff,Qty,Unit\n")


# R4.2
def test_format_a_detected(read):
    scans, *_ = read(A + "05/03/2026 10:00,X,1,each\n")
    assert scans[0].minute == datetime(2026, 3, 5, 10, 0)


def test_format_b_detected(read):
    scans, *_ = read(B + "2026-03-05T10:00:00,X,1,n\n")
    assert scans[0].qty_each == 1


def test_header_cells_trimmed(read):
    scans, *_ = read("Scanned At, SKU ,Qty,Unit\n05/03/2026 10:00,X,1,each\n")
    assert len(scans) == 1


def test_unknown_header(read):
    with pytest.raises(StockmergeError, match="unrecognised header: a,b,c"):
        read("a,b,c\n")


@pytest.mark.parametrize("content", [b"", b"\n\n  \n"])
def test_no_header_row(read, content):
    with pytest.raises(StockmergeError, match="no header row"):
        read(content)


def test_header_only(read):
    scans, n, s, msgs, path = read(A)
    assert scans == [] and msgs == [f"{path}: no valid rows"]


# R4.3
def test_blank_lines_ignored(read):
    scans, n, s, msgs, _ = read(A + "\n   \n,,,\n05/03/2026 10:00,X,1,each\n")
    assert len(scans) == 1 and msgs == [] and n == 1


def test_blank_lines_before_header(read):
    scans, *_ = read("\n\n" + A + "05/03/2026 10:00,X,1,each\n")
    assert len(scans) == 1


def test_five_fields_skipped(read):
    scans, n, s, msgs, _ = read(A + "05/03/2026 10:00,X,1,each,extra\n")
    assert scans == [] and "expected 4 fields, found 5" in msgs[0]


def test_b_note_unquoted_comma_skipped(read):
    scans, n, s, msgs, _ = read(B + "2026-03-05T10:00:00,X,1,a,b\n")
    assert scans == [] and s == 1


# R4.4
def test_blank_sku(read):
    scans, n, s, msgs, _ = read(A + "05/03/2026 10:00,  ,1,each\n")
    assert scans == [] and "blank SKU" in msgs[0]


def test_sku_trimmed(read):
    scans, *_ = read(A + "05/03/2026 10:00, 00123 ,1,each\n")
    assert scans[0].sku == "00123" and scans[0].sku_norm == "123"


# R4.5
@pytest.mark.parametrize("when,expected", [
    ("05/03/2026 14:30", datetime(2026, 3, 5, 14, 30)),
    ("5/3/2026 9:05", datetime(2026, 3, 5, 9, 5)),
])
def test_format_a_dates_ok(read, when, expected):
    scans, *_ = read(A + f"{when},X,1,each\n")
    assert scans[0].minute == expected


def test_format_a_bad_date(read):
    scans, n, s, msgs, _ = read(A + "31/02/2026 10:00,X,1,each\n")
    assert scans == [] and "bad date" in msgs[0]


# R4.6
@pytest.mark.parametrize("ts", ["2026-03-05T14:30:12", "2026-03-05T14:30:12.123456"])
def test_iso_ok(read, ts):
    scans, *_ = read(B + f"{ts},X,1,\n")
    assert scans[0].minute == datetime(2026, 3, 5, 14, 30)


@pytest.mark.parametrize("ts", [
    "2026-03-05T14:30:12Z",
    "2026-03-05T14:30:12+01:00",
    "2026-03-05",
    "٢٠٢٦-03-05T14:30:12",
])
def test_iso_rejected(read, ts):
    scans, n, s, msgs, _ = read(B + f"{ts},X,1,\n")
    assert scans == [] and "bad date" in msgs[0]


# R4.7
def test_seconds_truncated(read):
    scans, *_ = read(B + "2026-03-05T14:30:59,X,1,\n")
    assert scans[0].minute == datetime(2026, 3, 5, 14, 30)


# R4.8
@pytest.mark.parametrize("qty,expected", [("+5", 5), ("-3", -3)])
def test_quantity_ok(read, qty, expected):
    scans, *_ = read(A + f"05/03/2026 10:00,X,{qty},each\n")
    assert scans[0].qty_each == expected


@pytest.mark.parametrize("qty", ["5.0", "2.5", "", "1234567890"])
def test_quantity_rejected(read, qty):
    scans, n, s, msgs, _ = read(A + f"05/03/2026 10:00,X,{qty},each\n")
    assert scans == [] and "not a whole number" in msgs[0]


# R4.9
@pytest.mark.parametrize("qty,unit,expected", [("2", "case", 24), ("-1", "case", -12), ("1", " Case ", 12)])
def test_case_units(read, qty, unit, expected):
    scans, *_ = read(A + f"05/03/2026 10:00,X,{qty},{unit}\n")
    assert scans[0].qty_each == expected


def test_bad_unit(read):
    scans, n, s, msgs, _ = read(A + "05/03/2026 10:00,X,1,box\n")
    assert scans == [] and "bad unit" in msgs[0]


# R4.10
@pytest.mark.parametrize("note", ["", "moved from back room", "case of 12"])
def test_b_count_ignores_note(read, note):
    scans, *_ = read(B + f"2026-03-05T10:00:00,X,7,{note}\n")
    assert scans[0].qty_each == 7


# R4.12
def test_unclosed_quote_does_not_swallow_lines(read):
    content = B + '2026-03-05T10:00:00,X,1,"oops\n2026-03-05T10:01:00,Y,1,\n2026-03-05T10:02:00,Z,1,\n'
    scans, *_ = read(content)
    assert [s.sku for s in scans] == ["X", "Y", "Z"]


def test_quoted_comma_note_kept(read):
    scans, *_ = read(B + '2026-03-05T10:00:00,X,1,"a, b"\n')
    assert len(scans) == 1


def test_long_note(read):
    scans, *_ = read(B + "2026-03-05T10:00:00,X,1," + "n" * 200_000 + "\n")
    assert len(scans) == 1


# Warning format
def test_warning_line_number_counts_physical_lines(read):
    content = A + "05/03/2026 10:00,X,1,each\n\n05/03/2026 10:00,X,1,box\n"
    scans, n, s, msgs, path = read(content)
    assert msgs == [f"{path}:4: bad unit: box"]
    assert scans[0].record_no == 0


def test_record_numbers_include_skipped_rows(read):
    content = A + "bad,X,1,each\n05/03/2026 10:00,X,1,each\n"
    scans, n, s, *_ = read(content)
    assert scans[0].record_no == 1 and (n, s) == (2, 1)
