from decimal import Decimal

import pytest

from tsinvoice.model import FatalError
from tsinvoice.rates import Rate, find_rate, load_rates, price


def write(tmp_path, text):
    p = tmp_path / "rates.csv"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_load_rates_in_file_order(tmp_path):
    p = write(tmp_path, "pattern,hourly_rate\nAcme,100\n review ,80.50\n")
    assert load_rates(p, [].append) == [Rate("Acme", Decimal("100")),
                                        Rate("review", Decimal("80.50"))]


def test_empty_pattern_is_ignored_with_warning(tmp_path):
    p = write(tmp_path, "pattern,hourly_rate\n,100\nAcme,50\n")
    warnings = []
    assert load_rates(p, warnings.append) == [Rate("Acme", Decimal("50"))]
    assert warnings == [f"warning: {p}:2: empty pattern ignored"]


@pytest.mark.parametrize("text", [
    "pat,rate\nAcme,100\n",
    "",
    "pattern,hourly_rate\nAcme,lots\n",
    "pattern,hourly_rate\nAcme,-5\n",
    "pattern,hourly_rate\nAcme,NaN\n",
    "pattern,hourly_rate\nAcme\n",
])
def test_bad_rates_file_is_fatal(tmp_path, text):
    with pytest.raises(FatalError):
        load_rates(write(tmp_path, text), [].append)


def test_missing_rates_file_is_fatal(tmp_path):
    with pytest.raises(FatalError, match="cannot read"):
        load_rates(str(tmp_path / "nope.csv"), [].append)


def test_find_rate_substring_case_insensitive_client_or_description():
    rates = [Rate("acme", Decimal("100")), Rate("REVIEW", Decimal("80"))]
    assert find_rate("ACME Corp", "anything", rates) == Decimal("100")
    assert find_rate("Other", "code review", rates) == Decimal("80")
    assert find_rate("Other", "Design", rates) is None


def test_find_rate_first_match_wins():
    rates = [Rate("review", Decimal("80")), Rate("acme", Decimal("100"))]
    assert find_rate("Acme", "Review", rates) == Decimal("80")


def test_find_rate_normalises_whitespace():
    assert find_rate("Big   Co", "x", [Rate("big co", Decimal("1"))]) == Decimal("1")


def test_price_uses_minutes_over_sixty_half_up():
    assert price(18, Decimal("100")) == Decimal("30.00")
    assert price(6, Decimal("0.05")) == Decimal("0.01")    # 0.005 rounds up
    assert price(6, Decimal("0.15")) == Decimal("0.02")    # 0.015 rounds up, not to even
    assert str(price(6, Decimal("0"))) == "0.00"


def test_cp1252_rates_file_loads_with_warning(tmp_path):
    p = tmp_path / "rates.csv"
    p.write_text("pattern,hourly_rate\nCaf\u00e9,50\n", encoding="cp1252")
    warnings = []
    assert load_rates(str(p), warnings.append) == [Rate("Caf\u00e9", Decimal("50"))]
    assert warnings == [f"warning: {p}: not valid UTF-8, read as Windows-1252"]


def test_negative_zero_rate_loads_as_zero_and_prices_without_sign(tmp_path):
    p = write(tmp_path, "pattern,hourly_rate\nfree,-0\n")
    (rate,) = load_rates(p, [].append)
    assert str(price(30, rate.hourly_rate)) == "0.00"
