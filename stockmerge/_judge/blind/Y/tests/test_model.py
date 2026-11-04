import io

import pytest

from stockmerge.model import Warnings, normalise_sku


@pytest.mark.parametrize("text,expected", [(" 00ABC ", "abc"), ("000", "0"), ("123", "123")])
def test_normalise_sku(text, expected):
    assert normalise_sku(text) == expected


def test_warnings_with_path_and_line():
    s = io.StringIO()
    w = Warnings(s)
    w.add("a.csv", 4, "bad")
    assert s.getvalue() == "stockmerge: warning: a.csv:4: bad\n"
    assert w.messages == ["a.csv:4: bad"]


def test_warnings_path_only():
    s = io.StringIO()
    Warnings(s).add("a.csv", None, "no valid rows")
    assert s.getvalue() == "stockmerge: warning: a.csv: no valid rows\n"


def test_warnings_no_path():
    s = io.StringIO()
    Warnings(s).add(None, None, "hello")
    assert s.getvalue() == "stockmerge: warning: hello\n"


def test_warnings_default_stream_is_stderr(capsys):
    Warnings().add(None, None, "x")
    assert capsys.readouterr().err == "stockmerge: warning: x\n"
