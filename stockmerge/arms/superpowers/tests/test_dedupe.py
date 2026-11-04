from datetime import datetime

from stockmerge.dedupe import dedupe
from tests.factories import make_scan


def test_identical_rows_in_one_export_are_all_kept():
    a = make_scan(line=2)
    b = make_scan(line=3)
    assert dedupe([a, b]) == [a, b]


def test_overlap_across_exports_keeps_first_export():
    first = make_scan(export_index=0, line=2, sku_text="00123")
    second = make_scan(export_index=1, line=2, sku_text="123")
    assert dedupe([first, second]) == [first]


def test_max_count_not_sum_copies_from_first_export_with_that_many():
    e1 = [make_scan(export_index=0, line=n, sku_text="00123") for n in (2, 3)]
    e2 = [make_scan(export_index=1, line=n, sku_text="123") for n in (5, 6, 7)]
    assert dedupe(e1 + e2) == [e1[0], e1[1], e2[2]]


def test_different_locations_never_dedupe():
    a = make_scan(location="shop", export_index=0)
    b = make_scan(location="back", export_index=1)
    assert dedupe([a, b]) == [a, b]


def test_different_minute_or_qty_are_different_scans():
    a = make_scan(export_index=0)
    b = make_scan(export_index=1, minute=datetime(2026, 3, 5, 14, 31))
    c = make_scan(export_index=1, line=3, qty_each=2)
    assert dedupe([a, b, c]) == [a, b, c]


def test_result_is_in_input_order_regardless_of_argument_order():
    late = make_scan(export_index=1, line=2, sku_text="B")
    early = make_scan(export_index=0, line=9, sku_text="A")
    assert dedupe([late, early]) == [early, late]
