import re

from tests.factories import entry
from tsinvoice.model import Session
from tsinvoice.session_id import assign_ids, compute_id


def chain(tracker="desktop", arg_index=0):
    return [entry("2026-03-02T09:00", 7, tracker=tracker, arg_index=arg_index, line=2),
            entry("2026-03-02T09:07", 7, tracker=tracker, arg_index=arg_index, line=3)]


def test_compute_id_shape_and_stability():
    sid = compute_id(chain())
    assert re.fullmatch(r"s-[0-9a-f]{12}", sid)
    assert compute_id(chain()) == sid


def test_compute_id_ignores_input_position():
    assert compute_id(chain(arg_index=0)) == compute_id(chain(arg_index=5))


def test_compute_id_depends_on_content():
    assert compute_id(chain("desktop")) != compute_id(chain("phone"))


def test_assign_ids_blank_for_single_entry_and_distinct_on_collision():
    single = Session([entry("2026-03-02T08:00", 30)])
    s1, s2 = Session(chain()), Session(chain(arg_index=1))
    assign_ids([single, s1, s2])
    assert single.session_id == ""
    assert s1.session_id == compute_id(s1.entries)
    assert s2.session_id == s1.session_id + "-2"
