from datetime import datetime

from stockmerge.moves import link_moves


def t(h, m):
    return datetime(2026, 3, 5, h, m)


def mk(factory, n, location, qty, when, sku="X"):
    return factory(location=location, arg_index=n, record_no=0, qty_each=qty, minute=when, sku=sku)


def test_zero_qty_never_move(scan_factory):
    a = mk(scan_factory, 0, "shop", 0, t(10, 0))
    b = mk(scan_factory, 1, "back", 0, t(10, 5))
    assert link_moves([a, b]) == {}


def test_basic_pair(scan_factory):
    n = mk(scan_factory, 0, "back", -6, t(10, 5), "ABC")
    p = mk(scan_factory, 1, "shop", 6, t(11, 40), "abc")
    assert link_moves([n, p]) == {n.ident: "M0001", p.ident: "M0001"}


def test_positive_first(scan_factory):
    p = mk(scan_factory, 0, "shop", 6, t(9, 0))
    n = mk(scan_factory, 1, "back", -6, t(10, 0))
    assert set(link_moves([p, n])) == {p.ident, n.ident}


def test_120_minutes_links(scan_factory):
    n = mk(scan_factory, 0, "back", -1, t(10, 0))
    p = mk(scan_factory, 1, "shop", 1, t(12, 0))
    assert len(link_moves([n, p])) == 2


def test_121_minutes_does_not(scan_factory):
    n = mk(scan_factory, 0, "back", -1, t(10, 0))
    p = mk(scan_factory, 1, "shop", 1, t(12, 1))
    assert link_moves([n, p]) == {}


def test_same_location_never(scan_factory):
    n = mk(scan_factory, 0, "shop", -1, t(10, 0))
    p = mk(scan_factory, 1, "shop", 1, t(10, 1))
    assert link_moves([n, p]) == {}


def test_different_quantity_never(scan_factory):
    n = mk(scan_factory, 0, "back", -2, t(10, 0))
    p = mk(scan_factory, 1, "shop", 1, t(10, 1))
    assert link_moves([n, p]) == {}


def test_nearest_partner(scan_factory):
    n = mk(scan_factory, 0, "back", -5, t(10, 0))
    shop = mk(scan_factory, 1, "shop", 5, t(10, 30))
    store = mk(scan_factory, 2, "store", 5, t(10, 10))
    ids = link_moves([n, shop, store])
    assert set(ids) == {n.ident, store.ident}


def test_tie_goes_to_earlier_scan(scan_factory):
    n = mk(scan_factory, 0, "back", -5, t(10, 0))
    shop = mk(scan_factory, 1, "shop", 5, t(9, 50))
    store = mk(scan_factory, 2, "store", 5, t(10, 10))
    ids = link_moves([n, shop, store])
    assert set(ids) == {n.ident, shop.ident}


def test_first_negative_takes_partner(scan_factory):
    back = mk(scan_factory, 0, "back", -5, t(10, 0))
    store = mk(scan_factory, 1, "store", -5, t(10, 30))
    shop = mk(scan_factory, 2, "shop", 5, t(10, 20))
    ids = link_moves([store, shop, back])
    assert set(ids) == {back.ident, shop.ident}


def test_each_row_in_one_move(scan_factory):
    n1 = mk(scan_factory, 0, "back", -1, t(10, 0))
    n2 = mk(scan_factory, 1, "back", -1, t(10, 1))
    p = mk(scan_factory, 2, "shop", 1, t(10, 2))
    ids = link_moves([n1, n2, p])
    assert ids == {n1.ident: "M0001", p.ident: "M0001"}


def test_move_ids_in_order_formed(scan_factory):
    n1 = mk(scan_factory, 0, "back", -1, t(10, 0), "A")
    p1 = mk(scan_factory, 1, "shop", 1, t(10, 5), "A")
    n2 = mk(scan_factory, 2, "back", -1, t(9, 0), "B")
    p2 = mk(scan_factory, 3, "shop", 1, t(9, 5), "B")
    ids = link_moves([n1, p1, n2, p2])
    assert ids[n2.ident] == ids[p2.ident] == "M0001"
    assert ids[n1.ident] == ids[p1.ident] == "M0002"


def test_greedy_leaves_pair_unmatched(scan_factory):
    p2 = mk(scan_factory, 0, "shop", 5, t(8, 1))
    n1 = mk(scan_factory, 1, "back", -5, t(10, 0))
    p1 = mk(scan_factory, 2, "shop", 5, t(10, 5))
    n2 = mk(scan_factory, 3, "store", -5, t(10, 10))
    ids = link_moves([p2, n1, p1, n2])
    assert ids == {n1.ident: "M0001", p1.ident: "M0001"}
