"""Stages 2-3 and 'Reading any CSV file'."""

from datetime import datetime
from decimal import Decimal

import pytest

from tsinvoice.model import FatalError
from tsinvoice.readers import read_export, read_rates

A = "Client,Description,Start,End\n"
B = "client,task,start_iso,duration_minutes\n"


def warn(path, line, reason):
    return f"tsinvoice: warning: {path}:{line}: {reason}"


# ---- header detection -------------------------------------------------------

def test_format_a_detected(write_file):
    """Stage 3 header detection: Format A."""
    p = write_file("a.csv", A + "Acme,Design,08/10/2026 09:00,08/10/2026 10:00\n")
    entries, warns = read_export(p, "desk", 0)
    assert warns == []
    (e,) = entries
    assert (e.client, e.description, e.minutes) == ("Acme", "Design", 60)
    assert e.start == datetime(2026, 10, 8, 9, 0)
    assert e.order == (0, 2) and e.line == 2 and e.tracker == "desk"


def test_format_b_detected(write_file):
    """Stage 3 header detection: Format B; task -> description."""
    p = write_file("b.csv", B + "acme,design ,2026-10-08T09:07,7\n")
    (e,), warns = read_export(p, "phone", 1)
    assert warns == []
    assert e.description == "design" and e.end == datetime(2026, 10, 8, 9, 14)


@pytest.mark.parametrize("header", [
    " CLIENT , description,START,End\n",
    "Client,Description,Start,End,,\n",
])
def test_header_case_spacing_trailing_blank(write_file, header):
    """Stage 3: header trimmed, case-insensitive, trailing blank cells ignored."""
    p = write_file("a.csv", header + "Acme,Design,08/10/2026 09:00,08/10/2026 10:00\n")
    entries, _ = read_export(p, "d", 0)
    assert len(entries) == 1


def test_header_with_bom(write_file):
    """Reading: BOM removed."""
    p = write_file("a.csv", b"\xef\xbb\xbf" + (A + "Acme,D,08/10/2026 09:00,08/10/2026 10:00\n").encode())
    assert len(read_export(p, "d", 0)[0]) == 1


@pytest.mark.parametrize("content", [
    "Description,Client,Start,End\n",          # wrong order
    "Client,Description,Start,End,Notes\n",    # extra column
    "",                                         # zero-byte
    "\n,,,\n  \n",                              # only blank records
    '"Client,Description,Start,End\n',          # unterminated header
])
def test_unrecognised_header(write_file, content):
    """Stage 3 / Fatal messages: unrecognised header."""
    p = write_file("x.csv", content)
    with pytest.raises(FatalError) as ei:
        read_export(p, "d", 0)
    assert str(ei.value) == f"{p}: unrecognised header"


def test_blank_lines_before_header(write_file):
    """Glossary: header is the first non-blank record; line numbers are physical."""
    p = write_file("a.csv", "\n,,,\n" + A + "\nAcme,D,08/10/2026 09:00,bad\n")
    entries, warns = read_export(p, "d", 0)
    assert warns == [warn(p, 5, "invalid end")]


# ---- Format A bad rows -------------------------------------------------------

@pytest.mark.parametrize("row,reason", [
    ("Acme,D,08/10/2026 09:00,", "blank end"),
    ("Acme,D,08/10/2026 09:00,  ", "blank end"),
    ("Acme,D,,08/10/2026 09:00", "invalid start"),
    ("Acme,D,2026-10-08 09:00,08/10/2026 10:00", "invalid start"),
    ("Acme,D,08/10/2026 09:00,tomorrow", "invalid end"),
    ("Acme,D,08/10/2026 09:00,08/10/2026 09:00", "end is not after start"),
    ("Acme,D,08/10/2026 09:00,08/10/2026 08:00", "end is not after start"),
    ("  ,D,08/10/2026 09:00,08/10/2026 10:00", "blank client"),
    ("Acme,D,08/10/2026 09:00", "expected 4 fields, got 3"),
    ("Acme,D,08/10/2026 09:00,08/10/2026 10:00,x", "expected 4 fields, got 5"),
])
def test_format_a_bad_rows(write_file, row, reason):
    """Bad-row reasons table (Format A)."""
    p = write_file("a.csv", A + row + "\n")
    entries, warns = read_export(p, "d", 0)
    assert entries == [] and warns == [warn(p, 2, reason)]


def test_check_order(write_file):
    """Stage 3 check order: cell count before client before start."""
    p = write_file("a.csv", A + ",D,bad,bad,x\n,D,bad,\n")
    _, warns = read_export(p, "d", 0)
    assert warns == [warn(p, 2, "expected 4 fields, got 5"), warn(p, 3, "blank client")]


def test_single_digit_date_accepted(write_file):
    """Stage 3: single-digit day/month/hour accepted."""
    p = write_file("a.csv", A + "Acme,D,5/1/2026 9:00,5/1/2026 9:30\n")
    (e,), _ = read_export(p, "d", 0)
    assert e.start == datetime(2026, 1, 5, 9, 0) and e.minutes == 30


def test_blank_description_kept(write_file):
    """Stage 3: blank description allowed."""
    p = write_file("a.csv", A + "Acme,  ,08/10/2026 09:00,08/10/2026 10:00\n")
    (e,), warns = read_export(p, "d", 0)
    assert e.description == "" and warns == []


def test_extra_blank_cells_accepted(write_file):
    """Stage 3: extra cells allowed only if blank."""
    p = write_file("a.csv", A + "Acme,D,08/10/2026 09:00,08/10/2026 10:00,, \n")
    assert len(read_export(p, "d", 0)[0]) == 1


def test_text_trimmed_case_kept(write_file):
    """Stage 3: client/description outer spaces trimmed, case kept."""
    p = write_file("a.csv", A + "  ACME  Ltd , Design  Work ,08/10/2026 09:00,08/10/2026 10:00\n")
    (e,), _ = read_export(p, "d", 0)
    assert (e.client, e.description) == ("ACME  Ltd", "Design  Work")
    assert (e.client_key, e.desc_key) == ("acme ltd", "design work")


# ---- Format B ------------------------------------------------------------------

@pytest.mark.parametrize("start,expected", [
    ("2026-10-08T09:00+05:00", datetime(2026, 10, 8, 9, 0)),
    ("2026-10-08T09:00Z", datetime(2026, 10, 8, 9, 0)),
    ("2026-10-08 09:00", datetime(2026, 10, 8, 9, 0)),
    ("2026-10-08T09:00:30", datetime(2026, 10, 8, 9, 0)),
    ("2026-10-08T09:00:59.999", datetime(2026, 10, 8, 9, 0)),
])
def test_format_b_start_iso(write_file, start, expected):
    """Stage 3 Format B: offset/Z dropped, seconds truncated."""
    p = write_file("b.csv", B + f"acme,t,{start},30\n")
    (e,), warns = read_export(p, "p", 0)
    assert warns == [] and e.start == expected and e.start.tzinfo is None
    assert e.minutes == 30


@pytest.mark.parametrize("start", ["2026-10-08", "2026-10-08T09", "", "08/10/2026 09:00",
                                   "2026-13-08T09:00"])
def test_format_b_bad_start(write_file, start):
    """Bad-row reasons: invalid start_iso."""
    p = write_file("b.csv", B + f"acme,t,{start},30\n")
    assert read_export(p, "p", 0)[1] == [warn(p, 2, "invalid start_iso")]


@pytest.mark.parametrize("dur,ok", [
    ("30", True), ("30.0", True), (" 30.00 ", True),
    ("30.", False), ("29.5", False), ("0", False), ("0.0", False), ("-5", False),
    ("+5", False), ("1e2", False), ("3_0", False), ("", False),
    ("99999999999", False), ("9" * 5000, False),
])
def test_format_b_duration(write_file, dur, ok):
    """Bad-row reasons: invalid duration_minutes (incl. overflow)."""
    p = write_file("b.csv", B + f"acme,t,2026-10-08T09:00,{dur}\n")
    entries, warns = read_export(p, "p", 0)
    if ok:
        assert len(entries) == 1 and entries[0].minutes == 30
    else:
        assert warns == [warn(p, 2, "invalid duration_minutes")]


# ---- CSV reading quirks --------------------------------------------------------

def test_unterminated_quote_in_export(write_file):
    """Reading: unterminated quoted field is one bad row at its start line (R4.1)."""
    p = write_file("a.csv", A + "Acme,D,08/10/2026 09:00,08/10/2026 10:00\n"
                   'Acme,"oops,08/10/2026 11:00,08/10/2026 12:00\n'
                   "Acme,D,08/10/2026 13:00,08/10/2026 14:00\n")
    entries, warns = read_export(p, "d", 0)
    assert len(entries) == 1
    assert warns == [warn(p, 3, "unterminated quoted field")]


def test_unterminated_quote_huge_field(write_file):
    """Reading: field size limit raised, so a huge swallowed field is not fatal."""
    p = write_file("a.csv", A + '"' + "x" * 200_000 + "\n")
    entries, warns = read_export(p, "d", 0)
    assert entries == [] and warns == [warn(p, 2, "unterminated quoted field")]


def test_unterminated_blank_content(write_file):
    """Reading: an unterminated record is never blank."""
    p = write_file("a.csv", A + '"')
    assert read_export(p, "d", 0)[1] == [warn(p, 2, "unterminated quoted field")]


def test_quote_quirk_then_open_quote(write_file):
    """Reading: quirk then open quote gives one unterminated row."""
    p = write_file("a.csv", A + 'Acme,"Design"x,08/10/2026 09:00,"08/10/2026 10:00\n'
                   "Acme,D,08/10/2026 13:00,08/10/2026 14:00\n")
    entries, warns = read_export(p, "d", 0)
    assert entries == [] and warns == [warn(p, 2, "unterminated quoted field")]


def test_quote_quirk_multiline_no_false_detection(write_file):
    """Reading: '"A"c,"multi' + newline + '",...' is one valid row."""
    p = write_file("a.csv", A + '"A"c,"multi\n",08/10/2026 09:00,08/10/2026 10:00\n')
    (e,), warns = read_export(p, "d", 0)
    assert warns == [] and e.client == "Ac" and e.description == "multi\n".strip()


def test_mid_row_quote_quirk_read_normally(write_file):
    """Reading: '"Design" review' is read by the csv module, not fatal."""
    p = write_file("a.csv", A + 'Acme,"Design" review,08/10/2026 09:00,08/10/2026 10:00\n')
    (e,), warns = read_export(p, "d", 0)
    assert warns == [] and e.description == "Design review"


@pytest.mark.parametrize("nl", ["\r\n", "\r"])
def test_line_endings_line_numbers(write_file, nl):
    """Reading: CRLF and bare CR are physical line breaks."""
    text = nl.join([A.strip(), "", "Acme,D,08/10/2026 09:00,08/10/2026 10:00",
                    "Acme,D,x,y", ""])
    p = write_file("a.csv", text)
    entries, warns = read_export(p, "d", 0)
    assert len(entries) == 1 and entries[0].line == 3
    assert warns == [warn(p, 4, "invalid start")]


def test_u2028_is_ordinary_character(write_file):
    """Reading: U+2028 is not a line break."""
    p = write_file("a.csv", A + "Acme,De sign,08/10/2026 09:00,08/10/2026 10:00\nAcme,D,x,y\n")
    entries, warns = read_export(p, "d", 0)
    assert entries[0].description == "De sign"
    assert warns == [warn(p, 3, "invalid start")]


def test_multiline_field_reports_start_line(write_file):
    """Line number: a quoted multi-line field reports its start line."""
    p = write_file("a.csv", A + 'Acme,"two\nlines",08/10/2026 09:00,bad\nAcme,D,x,y\n')
    _, warns = read_export(p, "d", 0)
    assert warns == [warn(p, 2, "invalid end"), warn(p, 4, "invalid start")]


def test_blank_records_skipped(write_file):
    """Glossary: blank record ',,,' skipped silently but counted in line numbers."""
    p = write_file("a.csv", A + ",,,\n\n , , ,\nAcme,D,x,y\n")
    entries, warns = read_export(p, "d", 0)
    assert entries == [] and warns == [warn(p, 5, "invalid start")]


def test_undecodable_file(write_file):
    """Fatal messages: cannot read (not valid UTF-8)."""
    p = write_file("a.csv", (A + "Caf\xe9,D,08/10/2026 09:00,08/10/2026 10:00\n").encode("cp1252"))
    with pytest.raises(FatalError) as ei:
        read_export(p, "d", 0)
    assert str(ei.value).startswith(f"{p}: cannot read: ")


def test_missing_file(tmp_path):
    """Fatal messages: cannot read (missing)."""
    p = str(tmp_path / "nope.csv")
    with pytest.raises(FatalError) as ei:
        read_export(p, "d", 0)
    assert str(ei.value).startswith(f"{p}: cannot read: ")


# ---- rates -------------------------------------------------------------------------

def test_rates_valid(write_file):
    """Stage 2: rules keep file order, normalised pattern, Decimal rate."""
    p = write_file("r.csv", "Pattern , HOURLY_RATE,\n\n  Acme  Corp ,100\nbeta, 0 \n,,\n")
    rules = read_rates(p)
    assert [(r.pattern_key, r.rate) for r in rules] == [("acme corp", Decimal("100")),
                                                         ("beta", Decimal("0"))]


def test_rates_header_only(write_file):
    """Stage 2: header-only rates file is valid."""
    assert read_rates(write_file("r.csv", "pattern,hourly_rate\n")) == []


@pytest.mark.parametrize("content", ["", "\n\n", "pattern,rate\n", "hourly_rate,pattern\n",
                                     '"pattern,hourly_rate\n'])
def test_rates_bad_header(write_file, content):
    """Fatal messages: unrecognised rates header."""
    p = write_file("r.csv", content)
    with pytest.raises(FatalError) as ei:
        read_rates(p)
    assert str(ei.value) == f"{p}: unrecognised rates header"


@pytest.mark.parametrize("row,reason", [
    ("acme", "expected 2 fields, got 1"),
    ("acme,10,x", "expected 2 fields, got 3"),
    ("  ,10", "empty pattern"),
    ("acme,ten", "invalid hourly_rate"),
    ("acme,NaN", "invalid hourly_rate"),
    ("acme,1e2", "invalid hourly_rate"),
    ("acme,+5", "invalid hourly_rate"),
    ("acme,-5", "invalid hourly_rate"),
    ("acme,", "invalid hourly_rate"),
    ("acme,1,000", "expected 2 fields, got 3"),
    ("acme,5.", "invalid hourly_rate"),
    ('"acme,10', "unterminated quoted field"),
    (" ,x,y", "expected 2 fields, got 3"),  # rates check order: count first
    (" ,x", "empty pattern"),                # then pattern before rate
])
def test_rates_bad_rows(write_file, row, reason):
    """Fatal messages: invalid rates row (and rates check order)."""
    p = write_file("r.csv", "pattern,hourly_rate\nok,1\n" + row + "\n")
    with pytest.raises(FatalError) as ei:
        read_rates(p)
    assert str(ei.value) == f"{p}:3: invalid rates row: {reason}"


def test_rates_extra_blank_cell_ok(write_file):
    """Stage 2: extra cells allowed only if blank."""
    assert len(read_rates(write_file("r.csv", "pattern,hourly_rate\nacme,10.50, \n"))) == 1


def test_rates_crlf(write_file):
    """Reading: CRLF in the rates file."""
    p = write_file("r.csv", "pattern,hourly_rate\r\nacme,10\r\nbad\r\n")
    with pytest.raises(FatalError) as ei:
        read_rates(p)
    assert str(ei.value) == f"{p}:3: invalid rates row: expected 2 fields, got 1"


def test_rates_missing_file(tmp_path):
    """Fatal messages: rates file cannot read."""
    p = str(tmp_path / "r.csv")
    with pytest.raises(FatalError) as ei:
        read_rates(p)
    assert str(ei.value).startswith(f"{p}: cannot read: ")
