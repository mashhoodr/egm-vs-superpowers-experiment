from stockmerge.dedup import dedup


def test_case_equals_each(scan_factory):
    a = scan_factory(arg_index=0, qty_each=12)
    b = scan_factory(arg_index=1, qty_each=12)
    kept, removed = dedup([a, b])
    assert kept == [a] and removed == 1


def test_leading_zeros_equal(scan_factory):
    a = scan_factory(arg_index=0, sku="00123")
    b = scan_factory(arg_index=1, sku="123")
    kept, removed = dedup([a, b])
    assert kept == [a] and removed == 1


def test_different_locations_never_deduped(scan_factory):
    a = scan_factory(arg_index=0, location="shop")
    b = scan_factory(arg_index=1, location="back")
    assert dedup([a, b]) == ([a, b], 0)


def test_identical_rows_in_one_export_kept(scan_factory):
    a = scan_factory(record_no=0)
    b = scan_factory(record_no=1)
    assert dedup([a, b]) == ([a, b], 0)


def test_counts_two_and_one(scan_factory):
    rows = [scan_factory(arg_index=0, record_no=0), scan_factory(arg_index=0, record_no=1),
            scan_factory(arg_index=1, record_no=0)]
    kept, removed = dedup(rows)
    assert kept == rows[:2] and removed == 1


def test_counts_two_and_three(scan_factory):
    e1 = [scan_factory(arg_index=0, record_no=i) for i in range(2)]
    e2 = [scan_factory(arg_index=1, record_no=i) for i in range(3)]
    kept, removed = dedup(e1 + e2)
    assert kept == e1 + e2[:1] and removed == 2


def test_kept_rows_keep_own_sku(scan_factory):
    a = scan_factory(arg_index=0, record_no=0, sku="00123")
    b = scan_factory(arg_index=1, record_no=0, sku="123")
    c = scan_factory(arg_index=1, record_no=1, sku="123")
    kept, _ = dedup([a, b, c])
    assert [s.sku for s in kept] == ["00123", "123"]
