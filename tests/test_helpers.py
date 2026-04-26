import pytest
from beancount.core.number import Decimal

from beancount_dkb.helpers import IBANMatcher, fmt_number_de


def test_fmt_number_de():
    assert fmt_number_de("1") == Decimal(1)
    assert fmt_number_de("1,50") == Decimal(1.50)
    assert fmt_number_de("150") == Decimal(150)
    assert fmt_number_de("15,0") == Decimal(15)
    assert fmt_number_de("1234,0") == Decimal(1234)


def test_iban_matcher_ignores_empty_entries():
    with pytest.warns(UserWarning) as user_warnings:
        matcher = IBANMatcher([(" \t", "Assets:DKB:Empty")])

    assert matcher.account_for(None) is None
    assert matcher.account_for("") is None
    assert len(user_warnings) == 1
    assert user_warnings[0].message.args[0] == (
        "Ignoring empty iban_matcher entry for account Assets:DKB:Empty."
    )
