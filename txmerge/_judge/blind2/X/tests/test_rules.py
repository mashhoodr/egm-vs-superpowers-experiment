import pytest

from txmerge.model import TxmergeError
from txmerge.rules import categorise, load_rules


def load(tmp_path, text):
    p = tmp_path / "rules.csv"
    p.write_text(text, encoding="utf-8")
    return str(p), load_rules(str(p))


def test_case_insensitive_substring():
    rules = [("tesco", "Groceries")]
    assert categorise("TESCO STORES 123", rules) == "Groceries"


def test_first_rule_wins():
    rules = [("tesco", "Groceries"), ("tesco stores", "Other")]
    assert categorise("TESCO STORES", rules) == "Groceries"


def test_no_match_uncategorised():
    assert categorise("ANYTHING", [("tesco", "Groceries")]) == "Uncategorised"


def test_dot_and_star_are_literal(tmp_path):
    _, rules = load(tmp_path, "pattern,category\na.b,Dot\nx*,Star\n")
    assert categorise("AXB", rules) == "Uncategorised"
    assert categorise("A.B", rules) == "Dot"
    assert categorise("XX", rules) == "Uncategorised"
    assert categorise("X*", rules) == "Star"


def test_inner_whitespace_not_collapsed(tmp_path):
    _, rules = load(tmp_path, "pattern,category\ncosta coffee,Coffee\n")
    assert categorise("COSTA  COFFEE", rules) == "Uncategorised"
    assert categorise("COSTA COFFEE", rules) == "Coffee"


def test_skipped_rule_rows(tmp_path, capsys):
    path, rules = load(
        tmp_path,
        "pattern,category\n"
        ",\n"  # line 2: all blank, silent
        " ,Food\n"  # line 3
        "TESCO, \n"  # line 4
        ",A,B\n"  # line 5
        "ok\n"  # line 6
        " Tesco , Groceries \n",  # line 7
    )
    assert rules == [("tesco", "Groceries")]
    assert capsys.readouterr().err == (
        f"txmerge: warning: {path}:3: blank pattern; rule skipped\n"
        f"txmerge: warning: {path}:4: blank category; rule skipped\n"
        f"txmerge: warning: {path}:5: expected 2 cells, got 3; rule skipped\n"
        f"txmerge: warning: {path}:6: expected 2 cells, got 1; rule skipped\n"
    )


def test_bad_header(tmp_path):
    with pytest.raises(TxmergeError, match="header must be pattern,category"):
        load(tmp_path, "Pattern,Category\n")


def test_header_trimmed_and_bom(tmp_path):
    p = tmp_path / "rules.csv"
    p.write_bytes(b"\xef\xbb\xbf pattern , category\nx,Y\n")
    assert load_rules(str(p)) == [("x", "Y")]


def test_transfer_is_ordinary_category(tmp_path):
    _, rules = load(tmp_path, "pattern,category\nmove,Transfer\n")
    assert categorise("MOVE MONEY", rules) == "Transfer"


def test_header_only(tmp_path):
    _, rules = load(tmp_path, "pattern,category\n")
    assert rules == []
    assert categorise("TESCO", rules) == "Uncategorised"


def test_empty_rules_file(tmp_path):
    with pytest.raises(TxmergeError, match="file is empty"):
        load(tmp_path, "")
