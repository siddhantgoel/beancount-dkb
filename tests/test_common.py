from unittest import TestCase

from beancount.core.number import Decimal
from beancount_dkb._common import fmt_number_de


class CommonTestCase(TestCase):
    def test_fmt_number_de(self):
        self.assertEqual(fmt_number_de('1'), Decimal(1))
        self.assertEqual(fmt_number_de('1,50'), Decimal(1.50))
        self.assertEqual(fmt_number_de('150'), Decimal(150))
        self.assertEqual(fmt_number_de('15,0'), Decimal(15))
        self.assertEqual(fmt_number_de('1234,0'), Decimal(1234))
