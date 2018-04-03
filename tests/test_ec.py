from decimal import Decimal
from tempfile import gettempdir
from textwrap import dedent
from unittest import TestCase
import datetime
import os.path

from beancount_dkb import ECImporter
from beancount_dkb.ec import FIELDS


HEADER = ';'.join('"{}"'.format(field) for field in FIELDS)


def path_for_temp_file(name):
    return os.path.join(gettempdir(), name)


class ECImporterTestCase(TestCase):
    def setUp(self):
        super(ECImporterTestCase, self).setUp()

        self.iban = 'DE99999999999999999999'
        self.filename = path_for_temp_file('{}.csv'.format(self.iban))

    def tearDown(self):
        if os.path.isfile(self.filename):
            os.remove(self.filename)

        super(ECImporterTestCase, self).tearDown()

    def test_identify_correct(self):
        importer = ECImporter(self.iban, 'Assets:DKB:EC')

        with open(self.filename, 'wb') as fd:
            fd.write(dedent(f'''
                "Kontonummer:";"{self.iban} / Girokonto";

                "Von:";"01.01.2018";
                "Bis:";"31.01.2018";
                "Kontostand vom 31.01.2017:";"5.000,01 EUR";

                {HEADER};
            ''').lstrip().encode('utf-8'))

        with open(self.filename) as fd:
            self.assertTrue(importer.identify(fd))

    def test_identify_invalid_iban(self):
        other_iban = 'DE00000000000000000000'

        with open(self.filename, 'wb') as fd:
            fd.write(dedent(f'''
                "Kontonummer:";"{self.iban} / Girokonto";

                "Von:";"01.01.2018";
                "Bis:";"31.01.2018";
                "Kontostand vom 31.01.2017:";"5.000,01 EUR";

                {HEADER};
            ''').lstrip().encode('utf-8'))

        importer = ECImporter(other_iban, 'Assets:DKB:EC')

        with open(self.filename) as fd:
            self.assertFalse(importer.identify(fd))

    def test_extract_no_transactions(self):
        importer = ECImporter(self.iban, 'Assets:DKB:EC')

        with open(self.filename, 'wb') as fd:
            fd.write(dedent(f'''
                "Kontonummer:";"{self.iban} / Girokonto";

                "Von:";"01.01.2018";
                "Bis:";"31.01.2018";
                "Kontostand vom 31.01.2017:";"5.000,01 EUR";

                {HEADER};
            ''').lstrip().encode('utf-8'))

        with open(self.filename) as fd:
            self.assertFalse(importer.extract(fd))

    def test_extract_transactions(self):
        with open(self.filename, 'wb') as fd:
            fd.write(dedent(f'''
                "Kontonummer:";"{self.iban} / Girokonto";

                "Von:";"01.01.2018";
                "Bis:";"31.01.2018";
                "Kontostand vom 31.01.2017:";"5.000,01 EUR";

                {HEADER};
                "16.01.2018";"16.01.2018";"Lastschrift";"REWE Filialen Voll";"REWE SAGT DANKE.";"DE00000000000000000000";"AAAAAAAA";"-15,37";"000000000000000000    ";"0000000000000000000000";"";
            ''').lstrip().encode('utf-8'))  # NOQA

        importer = ECImporter(self.iban, 'Assets:DKB:EC',
                              file_encoding='utf-8')

        with open(self.filename) as fd:
            transactions = importer.extract(fd)

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].date, datetime.date(2018, 1, 16))

        self.assertEqual(len(transactions[0].postings), 1)
        self.assertEqual(transactions[0].postings[0].account, 'Assets:DKB:EC')
        self.assertEqual(transactions[0].postings[0].units.currency, 'EUR')
        self.assertEqual(transactions[0].postings[0].units.number,
                         Decimal('-15.37'))
