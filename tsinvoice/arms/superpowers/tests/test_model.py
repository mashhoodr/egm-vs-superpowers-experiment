from datetime import date

from tests.factories import entry
from tsinvoice.model import Session, norm


def test_norm_trims_collapses_and_ignores_case():
    assert norm("  Acme   Corp\t Ltd ") == "acme corp ltd"


def test_norm_unicode_casefold():
    assert norm("CAFÉ") == norm("café")
    assert norm("STRASSE") == norm("straße")


def test_entry_order_is_arg_index_then_line():
    assert entry("2026-03-02T09:00", 30, arg_index=1, line=7).order == (1, 7)


def test_session_uses_first_entry_text_and_start():
    s = Session([entry("2026-03-02T09:00", 7, client="Acme ", description="Design"),
                 entry("2026-03-02T09:07", 7, client="ACME", description="design")])
    assert s.client == "Acme "  # Session does not trim; the parser already trims
    assert s.description == "Design"
    assert s.date == date(2026, 3, 2)
    assert s.raw_minutes == 14


def test_session_minutes_round_up_to_multiple_of_six():
    assert Session([entry("2026-03-02T09:00", 14)]).minutes == 18
    assert Session([entry("2026-03-02T09:00", 12)]).minutes == 12
    assert Session([entry("2026-03-02T09:00", 1)]).minutes == 6


def test_session_id_defaults_blank():
    assert Session([entry("2026-03-02T09:00", 30)]).session_id == ""
