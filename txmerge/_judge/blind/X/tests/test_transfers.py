import datetime
from decimal import Decimal

from txmerge.model import Record
from txmerge.transfers import pair_transfers

BASE = datetime.date(2026, 1, 1)


def rec(account, amount, day=0, line=0):
    return Record(account, BASE + datetime.timedelta(days=day), Decimal(amount), "x", 0, line)


def run(records):
    for i, r in enumerate(records):
        if not r.line:
            r.line = i + 2
    records.sort(key=Record.sort_key)
    n = pair_transfers(records)
    return n, records


def test_window_three_days_links_four_does_not():
    out, inn = rec("A", "-10.00", 0), rec("B", "10.00", 3)
    assert run([out, inn])[0] == 1
    assert inn.category == "Transfer" and out.transfer_id == inn.transfer_id == "T0001"
    assert run([rec("A", "-10.00", 0), rec("B", "10.00", 4)])[0] == 0


def test_inflow_before_outflow_links():
    out, inn = rec("A", "-10.00", 2), rec("B", "10.00", 0)
    assert run([out, inn])[0] == 1 and inn.transfer_id == "T0001"


def test_closest_date_wins_and_tie_goes_to_first():
    out = rec("A", "-10.00", 3)
    far, near = rec("B", "10.00", 0), rec("C", "10.00", 4)
    run([out, far, near])
    assert near.transfer_id == "T0001" and far.transfer_id == ""

    out = rec("A", "-10.00", 3)
    before, after = rec("B", "10.00", 2), rec("C", "10.00", 4)
    run([out, before, after])
    assert before.transfer_id == "T0001" and after.transfer_id == ""


def test_two_outflows_one_inflow():
    o1, o2, i = rec("A", "-10.00", 0), rec("A", "-10.00", 1), rec("B", "10.00", 1)
    run([o1, o2, i])
    assert o1.transfer_id == "T0001" and o2.transfer_id == ""


def test_same_account_and_zero_never_link():
    # D7
    assert run([rec("A", "-10.00"), rec("A", "10.00")])[0] == 0
    assert run([rec("A", "0.00"), rec("B", "0.00")])[0] == 0


def test_ids_in_pair_order():
    # D12
    a = [rec("A", "-5.00", 0), rec("B", "5.00", 0), rec("A", "-7.00", 1), rec("B", "7.00", 1)]
    n, rs = run(a)
    assert n == 2
    assert [r.transfer_id for r in rs] == ["T0001", "T0001", "T0002", "T0002"]


def reference(records):
    """Stage 6 rule by scanning every inflow (records in output order)."""
    ids = [""] * len(records)
    counter = 0
    for oi, o in enumerate(records):
        if o.amount >= 0 or ids[oi]:
            continue
        best = None
        for ii, i in enumerate(records):
            if (i.amount > 0 and not ids[ii] and i.account != o.account
                    and i.amount == -o.amount):
                gap = abs((i.date - o.date).days)
                if gap <= 3 and (best is None or (gap, ii) < best):
                    best = (gap, ii)
        if best:
            counter += 1
            ids[oi] = ids[best[1]] = f"T{counter:04d}"
    return ids


def test_amount_index_matches_full_scan():
    # D27
    accounts = ["A", "B", "C"]
    rs = [rec(accounts[i % 3], "10.00", i % 7, line=i + 2) for i in range(50)]
    rs += [rec(accounts[(j + 1) % 3], "-10.00", j % 5, line=100 + j) for j in range(30)]
    rs.sort(key=Record.sort_key)
    expected = reference(rs)
    pair_transfers(rs)
    assert [r.transfer_id for r in rs] == expected
    assert any(expected)
