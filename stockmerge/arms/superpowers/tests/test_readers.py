from datetime import datetime

import pytest

from stockmerge.model import FatalError
from stockmerge.readers import read_export

A_HEADER = "Scanned At,SKU,Qty,Unit\n"
B_HEADER = "timestamp,barcode,count,note\n"


def write(tmp_path, text, name="in.csv", encoding="utf-8"):
    p = tmp_path / name
    p.write_bytes(text.encode(encoding))
    return str(p)


def read(path, warnings=None):
    sink = [] if warnings is None else warnings
    return read_export(path, "shop", 0, sink.append)


def test_format_a_each_and_case(tmp_path):
    path = write(tmp_path, A_HEADER
                 + "05/03/2026 14:30,00123,2,case\n"
                 + "05/03/2026 14:31,ABC,-3,each\n"
                 + "05/03/2026 14:32,ABC,-1,case\n")
    scans = read(path)
    assert [(s.sku_text, s.sku_key, s.qty_each, s.line) for s in scans] == [
        ("00123", "123", 24, 2), ("ABC", "abc", -3, 3), ("ABC", "abc", -12, 4)]
    assert scans[0].minute == datetime(2026, 3, 5, 14, 30)
    assert scans[0].location == "shop" and scans[0].export_index == 0


def test_format_a_unit_case_insensitive_and_trimmed(tmp_path):
    path = write(tmp_path, A_HEADER + "05/03/2026 14:30,X, 2 , CASE \n"
                 + "05/03/2026 14:30,X,1,Each\n")
    assert [s.qty_each for s in read(path)] == [24, 1]


def test_format_b_drops_seconds_and_ignores_note(tmp_path):
    path = write(tmp_path, B_HEADER + "2026-03-05T14:30:59,123,-3,1 case\n")
    [s] = read(path)
    assert s.minute == datetime(2026, 3, 5, 14, 30)
    assert s.qty_each == -3 and s.sku_text == "123"


def test_format_b_fraction_and_offset_accepted(tmp_path):
    path = write(tmp_path, B_HEADER + "2026-03-05T14:30:12.5,A,1,\n"
                 + "2026-03-05T14:30:12+05:00,A,1,\n")
    scans = read(path)
    assert [s.minute for s in scans] == [datetime(2026, 3, 5, 14, 30)] * 2
    assert all(s.minute.tzinfo is None for s in scans)


def test_format_b_date_without_time_is_bad_row(tmp_path):
    warnings = []
    path = write(tmp_path, B_HEADER + "2026-03-05,A,1,\n")
    assert read(path, warnings) == []
    assert len(warnings) == 1


def test_crlf_and_bom(tmp_path):
    path = write(tmp_path, "﻿ Scanned At , sku,QTY,unit\r\n"
                 "05/03/2026 14:30,X,1,each\r\n")
    [s] = read(path)
    assert s.sku_text == "X" and s.qty_each == 1


def test_trailing_empty_field_is_tolerated(tmp_path):
    path = write(tmp_path, "Scanned At,SKU,Qty,Unit,\n05/03/2026 14:30,X,1,each,\n")
    assert len(read(path)) == 1


def test_quoted_note_with_comma(tmp_path):
    path = write(tmp_path, B_HEADER + '2026-03-05T14:30:12,ABC,4,"moved, from back"\n')
    [s] = read(path)
    assert s.qty_each == 4


@pytest.mark.parametrize("row, reason_part", [
    ("05/03/2026 14:30,X,1.5,each", "quantity"),
    ("05/03/2026 14:30,X,1,box", "unit"),
    ("05/03/2026 14:30,  ,1,each", "SKU"),
    ("2026-03-05 14:30,X,1,each", "timestamp"),
    ("05/03/2026 14:30,X,1", "fields"),
])
def test_bad_rows_warn_and_skip(tmp_path, row, reason_part):
    warnings = []
    path = write(tmp_path, A_HEADER + row + "\n" + "05/03/2026 14:30,OK,1,each\n")
    scans = read(path, warnings)
    assert [s.sku_text for s in scans] == ["OK"]
    assert scans[0].line == 3
    assert len(warnings) == 1
    assert warnings[0].startswith(f"warning: {path}:2: ")
    assert reason_part in warnings[0]


def test_blank_lines_skipped_silently(tmp_path):
    warnings = []
    path = write(tmp_path, A_HEADER + "\n05/03/2026 14:30,X,1,each\n\n")
    scans = read(path, warnings)
    assert len(scans) == 1 and scans[0].line == 3 and warnings == []


def test_unknown_header_is_fatal(tmp_path):
    path = write(tmp_path, "date,item,qty\n")
    with pytest.raises(FatalError, match="header"):
        read(path)


def test_empty_file_is_fatal(tmp_path):
    with pytest.raises(FatalError):
        read(write(tmp_path, ""))


def test_missing_file_is_fatal(tmp_path):
    with pytest.raises(FatalError, match="cannot read"):
        read(str(tmp_path / "nope.csv"))


def test_non_utf8_file_is_fatal(tmp_path):
    path = write(tmp_path, B_HEADER + "2026-03-05T14:30:12,A,1,caf\xe9\n",
                 encoding="latin-1")
    with pytest.raises(FatalError, match="UTF-8"):
        read(path)


def test_unterminated_quote_does_not_swallow_later_rows(tmp_path):
    path = write(tmp_path, B_HEADER + '2026-03-05T14:30:12,A,1,"open note\n'
                 + "2026-03-05T14:31:00,B,2,\n")
    scans = read(path)
    assert [s.sku_text for s in scans if s.line == 3] == ["B"]
    assert all(s.line <= 3 for s in scans)


def test_multiline_quoted_note_is_reported_at_its_own_lines(tmp_path):
    warnings = []
    path = write(tmp_path, B_HEADER + '2026-03-05T14:30:12,A,1,"first\n'
                 + 'second"\n'
                 + "2026-03-05T14:32:00,C,1,\n")
    scans = read(path, warnings)
    assert [(s.sku_text, s.line) for s in scans] == [("A", 2), ("C", 4)]
    assert len(warnings) == 1 and f"{path}:3:" in warnings[0]


def test_huge_quantity_is_bad_row_not_crash(tmp_path):
    warnings = []
    path = write(tmp_path, A_HEADER + "05/03/2026 14:30,X," + "9" * 5000 + ",each\n"
                 + "05/03/2026 14:31,Y,1,each\n")
    scans = read(path, warnings)
    assert [s.sku_text for s in scans] == ["Y"]
    assert len(warnings) == 1 and f"{path}:2:" in warnings[0]


def test_oversized_field_is_bad_row_and_run_continues(tmp_path):
    warnings = []
    path = write(tmp_path, B_HEADER + "2026-03-05T14:30:00,A,1," + "n" * 200_000 + "\n"
                 + "2026-03-05T14:31:00,B,2,\n")
    scans = read(path, warnings)
    assert [s.sku_text for s in scans] == ["B"] and scans[0].line == 3
    assert len(warnings) == 1 and f"{path}:2:" in warnings[0]


def test_oversized_header_field_is_fatal(tmp_path):
    path = write(tmp_path, "x" * 200_000 + ",b,c,d\n")
    with pytest.raises(FatalError):
        read(path)


def test_unicode_line_separators_in_note_do_not_split_rows(tmp_path):
    path = write(tmp_path, B_HEADER + "2026-03-05T14:30:00,A,1,a\u2028b\n"
                 + "2026-03-05T14:31:00,B,2,c\x0cd\n"
                 + "2026-03-05T14:32:00,C,3,\n")
    warnings = []
    scans = read(path, warnings)
    assert warnings == []
    assert [(s.sku_text, s.line) for s in scans] == [("A", 2), ("B", 3), ("C", 4)]


def test_unquoted_comma_in_note_is_bad_row(tmp_path):
    warnings = []
    path = write(tmp_path, B_HEADER + "2026-03-05T14:30:12,ABC,4,moved, from back\n")
    assert read(path, warnings) == []
    assert len(warnings) == 1
