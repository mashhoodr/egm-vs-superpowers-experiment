import datetime
from decimal import Decimal

from txmerge.dedup import deduplicate
from txmerge.model import Row

D1 = datetime.date(2026, 3, 1)
D2 = datetime.date(2026, 3, 2)


def row(arg, line, desc="COFFEE", amount="-3.50", date=D1, account="cur"):
    return Row(account, date, desc, Decimal(amount), arg, line)


def test_overlap_of_two_exports_gives_one_copy():
    kept = deduplicate([row(0, 2), row(1, 5)])
    assert len(kept) == 1
    assert (kept[0].arg_index, kept[0].line_no) == (0, 2)


def test_repeats_inside_one_export_kept():
    assert len(deduplicate([row(0, 2), row(0, 3)])) == 2


def test_max_not_sum_and_first_text():
    rows = [
        row(0, 2, "Coffee Shop"),
        row(0, 3, "COFFEE SHOP"),
        row(1, 2, "coffee  shop"),
        row(1, 3, "coffee shop"),
        row(1, 4, "Coffee Shop"),
    ]
    kept = deduplicate(rows)
    assert len(kept) == 3
    assert [(r.arg_index, r.line_no) for r in kept] == [(0, 2), (0, 3), (1, 2)]
    assert all(r.description == "Coffee Shop" for r in kept)


def test_same_path_twice_count_unchanged():
    rows = [row(0, 2), row(0, 3), row(1, 2), row(1, 3)]
    assert len(deduplicate(rows)) == 2


def test_two_names_never_dedup():
    rows = [row(0, 2, account="a"), row(1, 2, account="b")]
    assert len(deduplicate(rows)) == 2


def test_case_and_whitespace_differences_are_one_copy():
    kept = deduplicate([row(0, 2, "Coffee  Shop"), row(1, 2, "coffee shop")])
    assert len(kept) == 1
    assert kept[0].description == "Coffee  Shop"


def test_different_text_date_or_amount_kept():
    assert len(deduplicate([row(0, 2, "COFFEE SHOP"), row(1, 2, "COFFEE SHO")])) == 2
    assert len(deduplicate([row(0, 2), row(1, 2, date=D2)])) == 2
    assert len(deduplicate([row(0, 2), row(1, 2, amount="-3.51")])) == 2


def test_mixed_formats_in_one_account_dedup():
    # Format A export (arg 0) and Format B export (arg 1) of the same account.
    kept = deduplicate([row(0, 2, "SHOP", "-12.50"), row(1, 7, "shop", "-12.50")])
    assert len(kept) == 1


def test_input_order_irrelevant_to_which_kept():
    kept = deduplicate([row(1, 2, "later"), row(0, 9, "LATER")])
    assert [(k.arg_index, k.description) for k in kept] == [(0, "LATER")]
