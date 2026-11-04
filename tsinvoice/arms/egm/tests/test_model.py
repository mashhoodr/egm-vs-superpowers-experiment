import pytest

from tsinvoice.model import Session, normalise
from tests.helpers import entry


def test_normalise_nfc_composed_and_decomposed_equal():
    """Glossary: Normalised text - NFC."""
    assert normalise("Café") == normalise("Café")


def test_normalise_casefold_sharp_s():
    """Glossary: Normalised text - case-folding."""
    assert normalise("Straße") == normalise("STRASSE")


def test_normalise_whitespace():
    """Glossary: Normalised text - trim and collapse."""
    assert normalise("  Acme \t  Corp\n ") == "acme corp"


@pytest.mark.parametrize("worked,billed", [(1, 6), (6, 6), (7, 12), (12, 12), (14, 18)])
def test_billed_minutes(worked, billed):
    """Stage 6: round up to a multiple of 6."""
    s = Session(entries=[entry("09:00", f"{9 + worked // 60:02d}:{worked % 60:02d}")])
    assert s.worked_minutes == worked
    assert s.billed_minutes == billed
