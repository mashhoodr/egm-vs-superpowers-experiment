import pytest

from stockmerge.model import FatalError
from stockmerge.rules import UNCATEGORISED, Rule, categorise, load_rules


def write(tmp_path, text):
    p = tmp_path / "rules.csv"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_load_and_first_match_wins(tmp_path):
    rules = load_rules(write(tmp_path, "pattern,category\nCOLA,Drinks\nco,Other\n"), [].append)
    assert rules == [Rule("cola", "Drinks"), Rule("co", "Other")]
    assert categorise("DIET-cola-330", rules) == "Drinks"
    assert categorise("COFFEE", rules) == "Other"


def test_no_match_is_uncategorised(tmp_path):
    rules = load_rules(write(tmp_path, "pattern,category\nTEA,Hot\n"), [].append)
    assert categorise("COLA", rules) == UNCATEGORISED == "Uncategorised"


def test_matches_normalised_sku(tmp_path):
    rules = load_rules(write(tmp_path, "pattern,category\n123,Cans\n"), [].append)
    assert categorise("00123", rules) == "Cans"


def test_header_tolerates_bom_case_and_spaces(tmp_path):
    rules = load_rules(write(tmp_path, "﻿ Pattern , CATEGORY\r\n x , Y \r\n"), [].append)
    assert rules == [Rule("x", "Y")]


def test_blank_pattern_skipped_with_warning(tmp_path):
    warnings = []
    path = write(tmp_path, "pattern,category\n,Everything\nA,Alpha\n")
    rules = load_rules(path, warnings.append)
    assert rules == [Rule("a", "Alpha")]
    assert warnings and warnings[0].startswith(f"warning: {path}:2: ")


def test_wrong_header_is_fatal(tmp_path):
    with pytest.raises(FatalError, match="header"):
        load_rules(write(tmp_path, "sku,cat\nA,B\n"), [].append)


def test_missing_rules_file_is_fatal(tmp_path):
    with pytest.raises(FatalError):
        load_rules(str(tmp_path / "none.csv"), [].append)


def test_pattern_with_leading_zeros_matches_raw_text(tmp_path):
    rules = load_rules(write(tmp_path, "pattern,category\n00123,Drinks\n"), [].append)
    assert categorise("00123", rules) == "Drinks"


def test_leading_zero_pattern_does_not_match_other_sku(tmp_path):
    rules = load_rules(write(tmp_path, "pattern,category\n0012,X\n"), [].append)
    assert categorise("5123", rules) == UNCATEGORISED


def test_trailing_empty_column_tolerated(tmp_path):
    warnings = []
    rules = load_rules(write(tmp_path, "pattern,category,\nA,Alpha,\n"), warnings.append)
    assert rules == [Rule("a", "Alpha")] and warnings == []


def test_stray_quote_affects_only_its_line(tmp_path):
    warnings = []
    path = write(tmp_path, 'pattern,category\n"abc,Drinks\nxyz,Food\n')
    rules = load_rules(path, warnings.append)
    assert Rule("xyz", "Food") in rules
    assert all(f"{path}:2:" in w for w in warnings)


def test_csv_error_on_rules_line_is_warning(tmp_path):
    warnings = []
    path = write(tmp_path, "pattern,category\n" + "p" * 200_000 + ",Big\nxyz,Food\n")
    rules = load_rules(path, warnings.append)
    assert rules == [Rule("xyz", "Food")]
    assert len(warnings) == 1 and f"{path}:2:" in warnings[0]
