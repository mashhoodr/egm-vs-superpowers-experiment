from datetime import date
from decimal import Decimal

from txmerge.dedupe import dedupe, normalise
from txmerge.model import Transaction


def t(desc, arg, line, account="cur", amount="-3.50", day=1):
    return Transaction(account, date(2026, 1, day), Decimal(amount), desc, (arg, line))


def test_normalise():
    assert normalise("  Costa   COFFEE \t x ") == "costa coffee x"


def test_identical_rows_in_one_file_are_all_kept():
    rows = [t("COFFEE", 0, 2), t("COFFEE", 0, 3)]
    assert dedupe(rows) == rows


def test_overlap_across_files_keeps_max_count_not_sum():
    rows = [t("COFFEE", 0, 2), t("COFFEE", 0, 3),
            t("COFFEE", 1, 2), t("COFFEE", 1, 3), t("COFFEE", 1, 4)]
    out = dedupe(rows)
    assert [r.source for r in out] == [(0, 2), (0, 3), (1, 2)]


def test_same_file_twice_changes_nothing():
    a = [t("COFFEE", 0, 2), t("TEA", 0, 3, amount="-2.00")]
    b = [t("COFFEE", 1, 2), t("TEA", 1, 3, amount="-2.00")]
    assert dedupe(a + b) == a


def test_whitespace_and_case_variants_match_and_first_text_wins():
    rows = [t("Costa  Coffee", 0, 2), t("COSTA COFFEE", 1, 5)]
    out = dedupe(rows)
    assert len(out) == 1 and out[0].description == "Costa  Coffee"


def test_first_text_wins_for_all_survivors():
    rows = [t("Costa Coffee", 0, 2), t("COSTA COFFEE", 1, 2), t("costa coffee", 1, 3)]
    out = dedupe(rows)
    assert [r.description for r in out] == ["Costa Coffee", "Costa Coffee"]
    assert [r.source for r in out] == [(0, 2), (1, 2)]


def test_different_accounts_never_merge():
    rows = [t("X", 0, 2, account="cur"), t("X", 1, 2, account="sav")]
    assert dedupe(rows) == rows


def test_different_date_or_amount_are_distinct():
    rows = [t("X", 0, 2), t("X", 1, 2, day=2), t("X", 1, 3, amount="-3.51")]
    assert dedupe(rows) == rows


def test_amount_scale_does_not_matter():
    rows = [t("X", 0, 2, amount="-3.5"), t("X", 1, 2, amount="-3.50")]
    assert len(dedupe(rows)) == 1


def test_output_is_in_source_order_regardless_of_input_order():
    rows = [t("B", 1, 2), t("A", 0, 2)]
    assert [r.source for r in dedupe(rows)] == [(0, 2), (1, 2)]
