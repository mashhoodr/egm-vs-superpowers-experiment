import csv
import io
from decimal import Decimal

from tests.factories import entry
from tsinvoice.model import Session
from tsinvoice.output import OUTPUT_HEADER, render_csv, session_row, sort_sessions


def test_sort_by_normalised_client_then_start_then_input_order():
    b = Session([entry("2026-03-01T09:00", 30, client="beta")])
    a_late = Session([entry("2026-03-02T09:00", 30, client="Alpha")])
    a_early = Session([entry("2026-03-01T09:00", 30, client="ALPHA", arg_index=1)])
    a_tie = Session([entry("2026-03-01T09:00", 30, client="alpha", arg_index=0, line=9)])
    assert sort_sessions([b, a_late, a_early, a_tie]) == [a_tie, a_early, a_late, b]


def test_session_row_format():
    s = Session([entry("2026-03-02T09:00", 14, client="Acme", description="Design")],
                session_id="s-abc")
    assert session_row(s, Decimal("30.00")) == ["2026-03-02", "Acme", "Design", "18", "30.00", "s-abc"]


def test_render_csv_header_and_newlines():
    text = render_csv([["2026-03-02", "Acme", "Design", "18", "30.00", ""]])
    assert text == "date,client,description,minutes,amount,session_id\n2026-03-02,Acme,Design,18,30.00,\n"


def test_render_csv_empty_is_header_only():
    assert render_csv([]) == ",".join(OUTPUT_HEADER) + "\n"


def test_write_csv_quotes_commas_and_quotes():
    row = ["2026-03-02", "Acme, Inc.", 'Fix "login" — café', "6", "1.00", ""]
    text = render_csv([row])
    assert list(csv.reader(io.StringIO(text)))[1] == row
