from datetime import datetime

from stockmerge.model import CASE_SIZE, Scan, sku_key


def test_case_size_is_twelve():
    assert CASE_SIZE == 12


def test_sku_key_trims_casefolds_and_strips_leading_zeros():
    assert sku_key("  00123 ") == "123"
    assert sku_key("AbC-9") == "abc-9"
    assert sku_key("A00") == "a00"


def test_sku_key_all_zeros_is_zero():
    assert sku_key("000") == "0"
    assert sku_key("0") == "0"


def test_sku_key_blank_stays_blank():
    assert sku_key("   ") == ""


def test_scan_input_order():
    s = Scan(location="shop", export_index=2, line=7, sku_text="X",
             sku_key="x", minute=datetime(2026, 3, 5, 14, 30), qty_each=1)
    assert s.input_order == (2, 7)
