from datetime import datetime

import pytest

from tsinvoice.model import FatalError
from tsinvoice.parse import read_tracker


def write(tmp_path, text, name="t.csv", encoding="utf-8"):
    p = tmp_path / name
    p.write_text(text, encoding=encoding)
    return str(p)


def read(path):
    warnings = []
    return read_tracker(path, "desk", 3, warnings.append), warnings


def test_format_a_row(tmp_path):
    p = write(tmp_path, "Client,Description,Start,End\n"
                        " Acme , Design  work ,02/03/2026 09:00,02/03/2026 10:30\n")
    entries, warnings = read(p)
    assert warnings == []
    (e,) = entries
    assert (e.tracker, e.arg_index, e.line) == ("desk", 3, 2)
    assert (e.client, e.description) == ("Acme", "Design  work")
    assert e.start == datetime(2026, 3, 2, 9, 0)
    assert e.end == datetime(2026, 3, 2, 10, 30)
    assert e.minutes == 90


def test_format_b_row_drops_offset_and_keeps_clock_time(tmp_path):
    p = write(tmp_path, "client,task,start_iso,duration_minutes\n"
                        "Acme,Design,2026-03-02T09:00:00Z,30\n"
                        "Acme,Design,2026-03-02T09:00:00+05:00,30.0\n"
                        "Acme,Design,2026-03-02T09:00:30,15\n")
    entries, warnings = read(p)
    assert warnings == []
    assert [e.start for e in entries] == [datetime(2026, 3, 2, 9, 0),
                                          datetime(2026, 3, 2, 9, 0),
                                          datetime(2026, 3, 2, 9, 0, 30)]
    assert all(e.start.tzinfo is None for e in entries)
    assert [e.minutes for e in entries] == [30, 30, 15]
    assert entries[2].end == datetime(2026, 3, 2, 9, 15, 30)


@pytest.mark.parametrize("duration", ["12.5", "0", "-5", "abc", "", "NaN", "inf", "1E+10", "1E+999999999"])
def test_format_b_bad_duration_is_skipped_with_warning(tmp_path, duration):
    p = write(tmp_path, "client,task,start_iso,duration_minutes\n"
                        f"Acme,Design,2026-03-02T09:00,{duration}\n"
                        "Acme,Design,2026-03-02T10:00,5\n")
    entries, warnings = read(p)
    assert len(entries) == 1
    assert len(warnings) == 1
    assert warnings[0].startswith(f"warning: {p}:2: ")


@pytest.mark.parametrize("row", [
    "Acme,Design,02/03/2026 10:00,02/03/2026 09:00",   # end before start
    "Acme,Design,02/03/2026 10:00,02/03/2026 10:00",   # end equals start
    "Acme,Design,2026-03-02 10:00,02/03/2026 11:00",   # wrong date format
    "Acme,Design,02/03/2026 10:00,",                   # blank end
    "Acme,Design,02/03/2026 10:00",                    # missing field
    "Acme,Design,02/03/2026 10:00,02/03/2026 11:00,x", # extra field
    " ,Design,02/03/2026 10:00,02/03/2026 11:00",      # empty client
])
def test_format_a_bad_rows_are_skipped_with_warning(tmp_path, row):
    p = write(tmp_path, "Client,Description,Start,End\n" + row + "\n")
    entries, warnings = read(p)
    assert entries == []
    assert len(warnings) == 1
    assert warnings[0].startswith(f"warning: {p}:2: ")


def test_format_b_bad_start_is_skipped(tmp_path):
    p = write(tmp_path, "client,task,start_iso,duration_minutes\nAcme,Design,yesterday,30\n")
    entries, warnings = read(p)
    assert entries == [] and len(warnings) == 1


def test_blank_lines_skipped_silently_and_line_numbers_kept(tmp_path):
    p = write(tmp_path, "Client,Description,Start,End\n\n"
                        "Acme,Design,02/03/2026 09:00,02/03/2026 10:00\n")
    entries, warnings = read(p)
    assert warnings == []
    assert entries[0].line == 3


def test_empty_description_is_allowed(tmp_path):
    p = write(tmp_path, "Client,Description,Start,End\nAcme,,02/03/2026 09:00,02/03/2026 10:00\n")
    entries, _ = read(p)
    assert entries[0].description == ""


def test_bom_and_spaced_header_tolerated(tmp_path):
    p = write(tmp_path, " client , task ,start_iso, duration_minutes\nAcme,Design,2026-03-02T09:00,30\n",
              encoding="utf-8-sig")
    entries, warnings = read(p)
    assert len(entries) == 1 and warnings == []


def test_header_only_file_gives_no_entries(tmp_path):
    p = write(tmp_path, "Client,Description,Start,End\n")
    assert read(p) == ([], [])


def test_unknown_header_is_fatal(tmp_path):
    p = write(tmp_path, "who,what,when\nAcme,Design,now\n")
    with pytest.raises(FatalError, match="header"):
        read(p)


def test_empty_file_is_fatal(tmp_path):
    p = write(tmp_path, "")
    with pytest.raises(FatalError):
        read(p)


def test_missing_file_is_fatal(tmp_path):
    with pytest.raises(FatalError, match="cannot read"):
        read(str(tmp_path / "nope.csv"))


def test_format_b_date_only_start_is_skipped_with_warning(tmp_path):
    p = write(tmp_path, "client,task,start_iso,duration_minutes\n"
                        "Acme,Design,2026-03-02,30\n"
                        "Acme,Design,2026-03-02T10:00,5\n")
    entries, warnings = read(p)
    assert len(entries) == 1
    assert warnings == [f"warning: {p}:2: start_iso '2026-03-02' has no time"]


def test_cp1252_tracker_file_is_read_with_warning(tmp_path):
    p = write(tmp_path, "Client,Description,Start,End\n"
                        "Caf\u00e9,Design,02/03/2026 09:00,02/03/2026 10:00\n",
              encoding="cp1252")
    entries, warnings = read(p)
    assert [e.client for e in entries] == ["Caf\u00e9"]
    assert warnings == [f"warning: {p}: not valid UTF-8, read as Windows-1252"]


def test_undecodable_tracker_file_is_fatal(tmp_path):
    p = tmp_path / "t.csv"
    p.write_bytes(b"Client,Description,Start,End\nCaf\x81,x,y,z\n")
    with pytest.raises(FatalError):
        read(str(p))
