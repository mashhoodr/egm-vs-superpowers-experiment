import pytest

from txmerge.categorise import UNCATEGORISED, categorise, load_rules
from txmerge.model import InputError


def test_case_insensitive_substring():
    assert categorise("Card purchase TESCO Metro", [("tesco", "Groceries")]) == "Groceries"


def test_first_match_wins():
    rules = [("tesco petrol", "Fuel"), ("tesco", "Groceries")]
    assert categorise("TESCO PETROL 123", rules) == "Fuel"
    assert categorise("TESCO STORE", rules) == "Groceries"


def test_no_match_is_uncategorised():
    assert categorise("SOMETHING", [("tesco", "Groceries")]) == UNCATEGORISED == "Uncategorised"


def test_load_rules(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text("pattern,category\nTESCO,Groceries\n\"SHELL, UK\",Fuel\n", encoding="utf-8")
    assert load_rules(str(p)) == [("TESCO", "Groceries"), ("SHELL, UK", "Fuel")]


def test_load_rules_bom_blank_and_spaces(tmp_path):
    p = tmp_path / "r.csv"
    p.write_bytes("﻿pattern , category\r\n\r\n  tesco  , Groceries \r\n,Everything\r\n".encode("utf-8"))
    assert load_rules(str(p)) == [("tesco", "Groceries")]


def test_load_rules_bad_header(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text("match,cat\nx,y\n", encoding="utf-8")
    with pytest.raises(InputError):
        load_rules(str(p))


def test_load_rules_missing_file(tmp_path):
    with pytest.raises(InputError):
        load_rules(str(tmp_path / "nope.csv"))


def test_load_rules_skips_empty_category(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text("pattern,category\ntesco,\nshell,  \namazon,Shopping\n", encoding="utf-8")
    assert load_rules(str(p)) == [("amazon", "Shopping")]


def test_load_rules_malformed_csv_is_input_error(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text('pattern,category\n"tesco,Groceries\nshell,Fuel\n', encoding="utf-8")
    with pytest.raises(InputError):
        load_rules(str(p))
