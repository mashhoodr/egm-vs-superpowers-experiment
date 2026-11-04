import pytest

from stockmerge.model import StockmergeError, Warnings
from stockmerge.rules import Rule, categorise, load_rules


@pytest.fixture
def load(write_file):
    def _load(content):
        path = write_file("rules.csv", content)
        w = Warnings()
        return load_rules(path, w), w.messages

    return _load


# R3.1
def test_wrong_header(load):
    with pytest.raises(StockmergeError, match="rules header must be pattern,category"):
        load("pat,cat\n")


def test_bom_and_spaces_header(load):
    rules, _ = load("﻿ pattern , category \nab,X\n".encode("utf-8"))
    assert rules == [Rule("ab", "X")]


# R3.2
@pytest.mark.parametrize("row,reason", [
    (" ,X", "blank pattern"),
    ("ab, ", "blank category"),
    ("ab,X,Y", "expected 2 fields, found 3"),
])
def test_bad_rows_skipped(load, row, reason):
    rules, msgs = load(f"pattern,category\n{row}\n")
    assert rules == [] and reason in msgs[0] and msgs[0].endswith(reason)


def test_header_only(load):
    assert load("pattern,category\n") == ([], [])


def test_empty_file(load):
    with pytest.raises(StockmergeError, match="no header row"):
        load("")


def test_bad_byte_row_skipped(load):
    rules, msgs = load(b"pattern,category\na\xff,X\nb,Y\n")
    assert rules == [Rule("b", "Y")] and "not valid UTF-8" in msgs[0]


# R3.3
def test_first_match_wins(load):
    rules, _ = load("pattern,category\nab,X\nabc,Y\n")
    assert categorise("abc", rules) == "X"


def test_substring_ignoring_case(load):
    rules, _ = load("pattern,category\nAB,X\n")
    assert categorise("xaby", rules) == "X"


# R3.4
def test_pattern_matches_normalised_sku(load):
    from stockmerge.model import normalise_sku
    rules, _ = load("pattern,category\nabc,X\n")
    assert categorise(normalise_sku("00ABC"), rules) == "X"


def test_zero_pattern_warns(load):
    rules, msgs = load("pattern,category\n0ab,X\n")
    assert len(rules) == 1 and "starts with 0" in msgs[0]


# R3.5
def test_reserved_category_warns(load):
    rules, msgs = load("pattern,category\nab,Move\n")
    assert rules == [Rule("ab", "Move")] and "also used by stockmerge" in msgs[0]


# R7.1
def test_no_match_uncategorised():
    assert categorise("zzz", [Rule("ab", "X")]) == "Uncategorised"
