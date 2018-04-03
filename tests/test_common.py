from functools import partial
import locale
from unittest import TestCase

from beancount_dkb._common import change_locale


class HelpersTestCase(TestCase):
    def test_change_locale(self):
        locale.setlocale(locale.LC_NUMERIC, 'en_US.UTF-8')

        getlocale = partial(locale.getlocale, locale.LC_NUMERIC)

        self.assertEqual(getlocale(), ('en_US', 'UTF-8'))

        with change_locale(locale.LC_NUMERIC, 'de_DE.UTF-8'):
            self.assertEqual(getlocale(), ('de_DE', 'UTF-8'))

        self.assertEqual(getlocale(), ('en_US', 'UTF-8'))
