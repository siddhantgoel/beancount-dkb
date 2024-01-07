from beancount.core.number import Decimal

from beancount_dkb.helpers import fmt_number_de


def test_fmt_number_de():
    assert fmt_number_de("1") == Decimal(1)
    assert fmt_number_de("1,50") == Decimal(1.50)
    assert fmt_number_de("150") == Decimal(150)
    assert fmt_number_de("15,0") == Decimal(15)
    assert fmt_number_de("1234,0") == Decimal(1234)
