import os
import stat

import pytest

from stockmerge.model import StockmergeError
from stockmerge.writer import write_csv

ROWS = [["shop", "ABC", "-12", "Food", ""]]


def test_replace_failure_leaves_nothing(tmp_path, monkeypatch):
    out = tmp_path / "inv.csv"
    out.write_bytes(b"old\n")

    def boom(*a):
        raise OSError("boom")

    monkeypatch.setattr("stockmerge.writer.os.replace", boom)
    with pytest.raises(StockmergeError, match="cannot write output"):
        write_csv(str(out), ROWS)
    assert out.read_bytes() == b"old\n"
    assert list(tmp_path.glob(".stockmerge-*.tmp")) == []


def test_new_file_mode_follows_umask(tmp_path):
    out = tmp_path / "inv.csv"
    old = os.umask(0o027)
    try:
        write_csv(str(out), ROWS)
    finally:
        os.umask(old)
    assert stat.S_IMODE(out.stat().st_mode) == 0o640


def test_existing_mode_kept(tmp_path):
    out = tmp_path / "inv.csv"
    out.write_text("old\n")
    os.chmod(out, 0o600)
    write_csv(str(out), ROWS)
    assert stat.S_IMODE(out.stat().st_mode) == 0o600
    assert out.read_text() == "location,sku,qty_each,category,move_id\nshop,ABC,-12,Food,\n"


def test_missing_folder(tmp_path):
    with pytest.raises(StockmergeError):
        write_csv(str(tmp_path / "nope" / "inv.csv"), ROWS)
