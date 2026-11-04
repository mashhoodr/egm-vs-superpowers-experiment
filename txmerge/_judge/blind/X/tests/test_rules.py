import datetime
from decimal import Decimal

import pytest

from txmerge.model import Record, TxmergeError
from txmerge.rules import categorise, load_rules


def rec(desc, transfer_id=""):
    return Record("A", datetime.date(2026, 1, 1), Decimal("-1.00"), desc, 0, 2,
                  transfer_id=transfer_id)


def load(write, content, msgs=None):
    p = write("rules.csv", content)
    return p, load_rules(p, (msgs if msgs is not None else []).append)


def test_case_insensitive_first_match_and_default(write):
    _, rules = load(write, "pattern,category\nCOFFEE,Food\ncoffee shop,Cafe\n")
    records = [rec("Big Coffee Shop"), rec("Rent")]
    categorise(records, rules)
    assert [r.category for r in records] == ["Food", "Uncategorised"]


def test_header_only_rules(write):
    # D9
    _, rules = load(write, "pattern,category\n")
    records = [rec("Coffee")]
    categorise(records, rules)
    assert records[0].category == "Uncategorised"


def test_invalid_rule_rows_warn_and_skip(write):
    # D8
    msgs = []
    p, rules = load(write, "pattern,category\ncoffee\n,Food\ncoffee,\ntea,Drinks\n", msgs)
    assert rules == [("tea", "Drinks")]
    assert msgs == [
        f"{p}:2: expected 2 fields, found 1",
        f"{p}:3: blank pattern",
        f"{p}:4: blank category",
    ]


def test_padded_cells(write):
    # D20
    _, rules = load(write, "pattern,category\n Coffee , Food \n")
    records = [rec("COFFEE")]
    categorise(records, rules)
    assert records[0].category == "Food"


@pytest.mark.parametrize("content", ["pat,cat\nx,y\n", ""])
def test_bad_header_or_empty(write, content):
    # D9
    with pytest.raises(TxmergeError) as e:
        load(write, content)
    assert str(e.value).endswith('rules header must be "pattern,category"')


def test_inner_whitespace_not_normalised(write):
    _, rules = load(write, "pattern,category\ncoffee shop,Food\n")
    records = [rec("COFFEE  SHOP")]
    categorise(records, rules)
    assert records[0].category == "Uncategorised"


def test_casefold_match(write):
    # D26
    _, rules = load(write, "pattern,category\nstraße,Street\n")
    records = [rec("STRASSE 5")]
    categorise(records, rules)
    assert records[0].category == "Street"


def test_rule_category_transfer_has_no_id(write):
    # D19
    _, rules = load(write, "pattern,category\nmove,Transfer\n")
    records = [rec("Move money")]
    categorise(records, rules)
    assert records[0].category == "Transfer" and records[0].transfer_id == ""


def test_transfer_records_skipped(write):
    _, rules = load(write, "pattern,category\nmove,Other\n")
    r = rec("Move money", transfer_id="T0001")
    r.category = "Transfer"
    categorise([r], rules)
    assert r.category == "Transfer"
