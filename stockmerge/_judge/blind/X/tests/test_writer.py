import os
import stat
from datetime import datetime

import pytest

from stockmerge.model import FatalError
from stockmerge.rules import Rule
from stockmerge.writer import render, write_atomic
from tests.factories import make_scan


def test_header_and_row_format():
    s = make_scan(location="shop", sku_text="00123", qty_each=-24)
    text = render([s], [Rule("123", "Cans")], {s.input_order: "M1"})
    assert text == "location,sku,qty_each,category,move_id\nshop,00123,-24,Cans,M1\n"


def test_blank_move_id_and_uncategorised():
    text = render([make_scan(sku_text="X")], [], {})
    assert text.splitlines()[1] == "shop,X,1,Uncategorised,"


def test_sorted_by_location_sku_key_minute_input_order():
    rows = [
        make_scan(location="shop", sku_text="B", line=2, qty_each=10),
        make_scan(location="back", sku_text="Z", line=3, qty_each=11),
        make_scan(location="shop", sku_text="a", line=4, qty_each=12,
                  minute=datetime(2026, 3, 5, 15, 0)),
        make_scan(location="shop", sku_text="A", line=5, qty_each=13,
                  minute=datetime(2026, 3, 5, 9, 0)),
        make_scan(location="shop", sku_text="A", line=1, qty_each=14,
                  minute=datetime(2026, 3, 5, 9, 0)),
    ]
    lines = render(rows, [], {}).splitlines()[1:]
    assert lines == [
        "back,Z,11,Uncategorised,",
        "shop,A,14,Uncategorised,",
        "shop,A,13,Uncategorised,",
        "shop,a,12,Uncategorised,",
        "shop,B,10,Uncategorised,",
    ]
    assert render(rows, [], {}) == render(list(reversed(rows)), [], {})


def test_ties_broken_by_input_order():
    rows = [
        make_scan(export_index=1, line=2, qty_each=3),
        make_scan(export_index=0, line=9, qty_each=2),
        make_scan(export_index=0, line=4, qty_each=1),
    ]
    expected = ["shop,A1,1,Uncategorised,", "shop,A1,2,Uncategorised,", "shop,A1,3,Uncategorised,"]
    assert render(rows, [], {}).splitlines()[1:] == expected
    assert render(list(reversed(rows)), [], {}).splitlines()[1:] == expected


def test_values_with_commas_are_quoted():
    text = render([make_scan(location="shop, front")], [], {})
    assert text.splitlines()[1].startswith('"shop, front",')


def test_write_atomic(tmp_path):
    target = tmp_path / "out.csv"
    write_atomic(str(target), "a\n")
    assert target.read_bytes() == b"a\n"
    assert [p.name for p in tmp_path.iterdir()] == ["out.csv"]


def test_write_atomic_missing_directory_is_fatal(tmp_path):
    with pytest.raises(FatalError, match="cannot write"):
        write_atomic(str(tmp_path / "missing" / "out.csv"), "a\n")


def test_write_atomic_uses_umask_mode(tmp_path):
    target = tmp_path / "out.csv"
    previous = os.umask(0o022)
    try:
        write_atomic(str(target), "a\n")
    finally:
        os.umask(previous)
    assert stat.S_IMODE(os.stat(target).st_mode) == 0o644


def test_write_atomic_unencodable_text_is_fatal_and_leaves_no_temp(tmp_path):
    with pytest.raises(FatalError, match="cannot write"):
        write_atomic(str(tmp_path / "out.csv"), "bad \udcff\n")
    assert list(tmp_path.iterdir()) == []
