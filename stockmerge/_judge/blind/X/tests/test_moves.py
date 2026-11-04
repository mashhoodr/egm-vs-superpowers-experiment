from datetime import datetime, timedelta

from stockmerge.moves import link_moves
from tests.factories import make_scan

T0 = datetime(2026, 3, 5, 14, 0)


def scan(location, qty, minutes=0, export_index=0, line=2, sku="A1"):
    return make_scan(location=location, qty_each=qty, minute=T0 + timedelta(minutes=minutes),
                     export_index=export_index, line=line, sku_text=sku)


def test_simple_move_links_both_rows():
    out = scan("shop", -5, export_index=0)
    back = scan("back", 5, minutes=30, export_index=1)
    assert link_moves([out, back]) == {out.input_order: "M1", back.input_order: "M1"}


def test_exactly_two_hours_counts_and_more_does_not():
    neg = scan("shop", -5, export_index=0)
    edge = scan("back", 5, minutes=120, export_index=1)
    assert link_moves([neg, edge]) != {}
    late = scan("back", 5, minutes=121, export_index=1)
    assert link_moves([neg, late]) == {}


def test_positive_before_negative_still_links():
    neg = scan("shop", -5, minutes=60, export_index=0)
    pos = scan("back", 5, minutes=0, export_index=1)
    assert len(link_moves([neg, pos])) == 2


def test_requires_exact_opposite_and_same_sku_and_other_location():
    neg = scan("shop", -5, export_index=0)
    assert link_moves([neg, scan("back", 4, export_index=1)]) == {}
    assert link_moves([neg, scan("back", 5, export_index=1, sku="B2")]) == {}
    assert link_moves([neg, scan("shop", 5, export_index=0, line=3)]) == {}


def test_sku_compared_normalised():
    neg = scan("shop", -12, export_index=0, sku="00123")
    pos = scan("back", 12, export_index=1, sku="123")
    assert len(link_moves([neg, pos])) == 2


def test_closest_partner_wins():
    neg = scan("shop", -5, minutes=60, export_index=0)
    far = scan("back", 5, minutes=0, export_index=1, line=2)
    near = scan("store", 5, minutes=70, export_index=2, line=2)
    moves = link_moves([neg, far, near])
    assert moves == {neg.input_order: "M1", near.input_order: "M1"}


def test_tie_goes_to_earliest_in_scan_order():
    neg = scan("shop", -5, minutes=60, export_index=0)
    before = scan("back", 5, minutes=30, export_index=1)
    after = scan("store", 5, minutes=90, export_index=2)
    assert link_moves([neg, after, before]) == {neg.input_order: "M1", before.input_order: "M1"}


def test_each_row_in_at_most_one_move_and_ids_follow_scan_order():
    n1 = scan("shop", -5, minutes=0, export_index=0, line=2)
    n2 = scan("shop", -5, minutes=10, export_index=0, line=3)
    p1 = scan("back", 5, minutes=5, export_index=1, line=2)
    p2 = scan("back", 5, minutes=100, export_index=1, line=3)
    moves = link_moves([n2, p2, n1, p1])
    assert moves == {n1.input_order: "M1", p1.input_order: "M1",
                     n2.input_order: "M2", p2.input_order: "M2"}


def test_greedy_does_not_search_for_more_moves():
    # n1 (first in scan order) takes p_shared (closest); n2 then has no partner,
    # even though pairing n1 with p_other would have linked both.
    n1 = scan("shop", -5, minutes=0, export_index=0, line=2)
    n2 = scan("shop", -5, minutes=100, export_index=0, line=3)
    p_shared = scan("back", 5, minutes=50, export_index=1, line=2)
    p_other = scan("store", 5, minutes=-60, export_index=2, line=2)
    moves = link_moves([n1, n2, p_shared, p_other])
    assert moves[n1.input_order] == "M1" and moves[p_shared.input_order] == "M1"
    assert n2.input_order not in moves
    assert p_other.input_order not in moves


def test_zero_quantity_never_moves():
    assert link_moves([scan("shop", 0), scan("back", 0, export_index=1)]) == {}


def test_same_minute_tie_goes_to_earlier_location_name():
    neg = scan("shop", -5, minutes=60, export_index=0)
    back = scan("back", 5, minutes=70, export_index=1)
    alpha = scan("alpha", 5, minutes=70, export_index=2)
    assert link_moves([neg, back, alpha]) == {neg.input_order: "M1", alpha.input_order: "M1"}


def test_same_minute_same_location_tie_goes_to_lower_export_index():
    neg = scan("shop", -5, minutes=60, export_index=0)
    later = scan("back", 5, minutes=70, export_index=2)
    earlier = scan("back", 5, minutes=70, export_index=1)
    assert link_moves([neg, later, earlier]) == {neg.input_order: "M1", earlier.input_order: "M1"}
