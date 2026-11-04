import datetime
from decimal import Decimal

from txmerge.ledger import sort_rows
from txmerge.model import Row
from txmerge.transfers import pair_transfers, transfer_id


def r(account, date, amount, line):
    m, d = date
    return Row(account, datetime.date(2026, m, d), "X", Decimal(amount), 0, line)


def ids_for(*rows):
    ledger = sort_rows(list(rows))
    by_line = {row.line_no: tid for row, tid in zip(ledger, pair_transfers(ledger))}
    return sorted(by_line.items())


def test_gap_3_pairs():
    assert ids_for(r("cur", (3, 1), "-50", 1), r("card", (3, 4), "50", 2)) == [
        (1, "T0001"),
        (2, "T0001"),
    ]


def test_gap_4_no_pair():
    assert ids_for(r("cur", (3, 1), "-50", 1), r("card", (3, 5), "50", 2)) == [(1, ""), (2, "")]


def test_inflow_may_come_first():
    assert ids_for(r("card", (2, 27), "50", 1), r("cur", (3, 1), "-50", 2)) == [
        (1, "T0001"),
        (2, "T0001"),
    ]


def test_equal_gaps_earlier_position_wins():
    out = ids_for(
        r("cur", (3, 1), "-50", 1), r("card", (3, 2), "50", 2), r("card", (3, 2), "50", 3)
    )
    assert out == [(1, "T0001"), (2, "T0001"), (3, "")]


def test_greedy_earlier_outflow_takes_inflow():
    out = ids_for(
        r("cur", (3, 1), "-50", 1), r("cur", (3, 3), "-50", 2), r("card", (3, 3), "50", 3)
    )
    assert out == [(1, "T0001"), (2, ""), (3, "T0001")]


def test_same_account_no_pair():
    assert ids_for(r("cur", (3, 1), "-50", 1), r("cur", (3, 2), "50", 2)) == [(1, ""), (2, "")]


def test_smallest_gap_wins():
    out = ids_for(
        r("card", (3, 1), "50", 1), r("cur", (3, 3), "-50", 2), r("card", (3, 4), "50", 3)
    )
    assert out == [(1, ""), (2, "T0001"), (3, "T0001")]


def test_one_inflow_cannot_serve_two_outflows():
    out = ids_for(
        r("cur", (3, 1), "-50", 1), r("sav", (3, 1), "-50", 2), r("card", (3, 1), "50", 3)
    )
    assert [tid for _, tid in out].count("T0001") == 2
    assert "T0002" not in [tid for _, tid in out]


def test_amount_must_match_exactly():
    assert ids_for(r("cur", (3, 1), "-500.00", 1), r("card", (3, 1), "499.99", 2)) == [
        (1, ""),
        (2, ""),
    ]


def test_zero_amounts_never_pair():
    assert ids_for(r("cur", (3, 1), "-0.00", 1), r("card", (3, 1), "0.00", 2)) == [
        (1, ""),
        (2, ""),
    ]


def test_ids_in_pairing_order():
    out = ids_for(
        r("cur", (3, 1), "-10", 1),
        r("card", (3, 1), "10", 2),
        r("cur", (3, 5), "-20", 3),
        r("card", (3, 6), "20", 4),
    )
    assert out == [(1, "T0001"), (2, "T0001"), (3, "T0002"), (4, "T0002")]


def test_transfer_id_format():
    assert transfer_id(1) == "T0001"
    assert transfer_id(9999) == "T9999"
    assert transfer_id(10000) == "T10000"
