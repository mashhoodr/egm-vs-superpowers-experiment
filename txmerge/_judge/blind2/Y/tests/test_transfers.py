from datetime import date
from decimal import Decimal

from txmerge.model import Transaction
from txmerge.transfers import order, pair_transfers


def t(account, day, amount, line=2, arg=0, desc="X"):
    return Transaction(account, date(2026, 1, day), Decimal(amount), desc, (arg, line))


def test_order_by_date_account_then_source():
    a = t("sav", 1, "1", arg=1, line=2)
    b = t("cur", 1, "1", arg=0, line=9)
    c = t("cur", 1, "1", arg=0, line=3)
    d = t("cur", 2, "1", arg=0, line=1)
    assert order([d, a, b, c]) == [c, b, a, d]


def test_simple_pair():
    rows = order([t("cur", 1, "-100"), t("sav", 2, "100", arg=1)])
    assert pair_transfers(rows) == ["T0001", "T0001"]


def test_window_is_three_days_inclusive():
    assert pair_transfers(order([t("cur", 1, "-100"), t("sav", 4, "100", arg=1)])) == ["T0001"] * 2
    assert pair_transfers(order([t("cur", 1, "-100"), t("sav", 5, "100", arg=1)])) == ["", ""]


def test_inflow_may_precede_outflow():
    rows = order([t("sav", 1, "100", arg=1), t("cur", 3, "-100")])
    assert pair_transfers(rows) == ["T0001", "T0001"]


def test_same_account_never_pairs():
    rows = order([t("cur", 1, "-100"), t("cur", 1, "100", line=3)])
    assert pair_transfers(rows) == ["", ""]


def test_amount_must_match_exactly():
    rows = order([t("cur", 1, "-100.00"), t("sav", 1, "100.01", arg=1)])
    assert pair_transfers(rows) == ["", ""]


def test_closest_date_wins():
    out = t("cur", 5, "-50")
    far = t("sav", 2, "50", arg=1)
    near = t("card", 6, "50", arg=2)
    rows = order([out, far, near])
    ids = dict(zip(rows, pair_transfers(rows)))
    assert ids[out] == ids[near] == "T0001" and ids[far] == ""


def test_tie_goes_to_earliest_in_output_order():
    out = t("cur", 5, "-50")
    before = t("sav", 4, "50", arg=1)
    after = t("card", 6, "50", arg=2)
    rows = order([out, before, after])
    ids = dict(zip(rows, pair_transfers(rows)))
    assert ids[before] == "T0001" and ids[after] == ""


def test_each_row_in_one_pair_and_ids_increment_in_outflow_order():
    o1 = t("cur", 1, "-100", line=2)
    o2 = t("cur", 2, "-100", line=3)
    i1 = t("sav", 1, "100", arg=1, line=2)
    i2 = t("sav", 2, "100", arg=1, line=3)
    rows = order([o1, o2, i1, i2])
    ids = dict(zip(rows, pair_transfers(rows)))
    assert ids[o1] == ids[i1] == "T0001"
    assert ids[o2] == ids[i2] == "T0002"


def test_greedy_earlier_outflow_takes_contested_inflow():
    o1 = t("cur", 1, "-100", line=2)
    o2 = t("card", 3, "-100", arg=2)
    i = t("sav", 2, "100", arg=1)
    rows = order([o1, o2, i])
    ids = dict(zip(rows, pair_transfers(rows)))
    assert ids[o1] == ids[i] == "T0001" and ids[o2] == ""


def test_credit_card_payoff_pairs():
    pay = t("cur", 10, "-500.00", desc="CARD PAYMENT")
    rec = t("card", 11, "500.00", arg=1, desc="PAYMENT RECEIVED THANK YOU")
    rows = order([pay, rec])
    assert pair_transfers(rows) == ["T0001", "T0001"]


def test_unmatched_and_zero_rows_stay_blank():
    rows = order([t("cur", 1, "-10"), t("cur", 1, "0", line=3), t("sav", 1, "0", arg=1)])
    assert pair_transfers(rows) == ["", "", ""]


def test_id_widens_past_9999():
    rows = []
    for i in range(10000):
        rows.append(t("cur", 1, f"-{i + 1}", line=i + 2))
        rows.append(t("sav", 1, f"{i + 1}", arg=1, line=i + 2))
    ids = pair_transfers(order(rows))
    assert "T10000" in ids
