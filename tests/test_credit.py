from decimal import Decimal
from tempfile import gettempdir
from textwrap import dedent
from unittest import TestCase
import datetime
import os

from beancount.core.data import Amount, Balance

from beancount_dkb import CreditImporter
from beancount_dkb.credit import FIELDS


HEADER = ';'.join('"{}"'.format(field) for field in FIELDS)


def path_for_temp_file(name):
    return os.path.join(gettempdir(), name)


def _format(string, kwargs):
    return dedent(string).format(**kwargs).lstrip().encode('utf-8')


class CreditImporterTestCase(TestCase):
    def setUp(self):
        super(CreditImporterTestCase, self).setUp()

        self.card_number = '1234********5678'
        self.filename = path_for_temp_file('{}.csv'.format(self.card_number))

    def tearDown(self):
        if os.path.isfile(self.filename):
            os.remove(self.filename)

        super(CreditImporterTestCase, self).tearDown()

    def test_multiple_headers(self):
        importer = CreditImporter(self.card_number, 'Assets:DKB:Credit')

        common = '''
            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Saldo:";"5.000,01 EUR";
            "Datum:";"15.02.2018";
        '''

        # previous header format
        with open(self.filename, 'wb') as fd:
            fd.write(_format('''
                "Kreditkarte:";"{card_number} Kreditkarte";

                {common}

            ''', dict(card_number=self.card_number, common=common)))

        with open(self.filename) as fd:
            self.assertTrue(importer.identify(fd))

        # latest header format
        with open(self.filename, 'wb') as fd:
            fd.write(_format('''
                "Kreditkarte:";"{card_number}";

                {common}

            ''', dict(card_number=self.card_number, common=common)))

        with open(self.filename) as fd:
            self.assertTrue(importer.identify(fd))

    def test_identify_correct(self):
        importer = CreditImporter(self.card_number, 'Assets:DKB:Credit')

        with open(self.filename, 'wb') as fd:
            fd.write(_format('''
                "Kreditkarte:";"{card_number} Kreditkarte";

                "Von:";"01.01.2018";
                "Bis:";"31.01.2018";
                "Saldo:";"5.000,01 EUR";
                "Datum:";"15.02.2018";

                {header};
            ''', dict(card_number=self.card_number, header=HEADER)))

        with open(self.filename) as fd:
            self.assertTrue(importer.identify(fd))

    def test_identify_invalid_iban(self):
        other_iban = '5678********1234'

        with open(self.filename, 'wb') as fd:
            fd.write(_format('''
                "Kreditkarte:";"{card_number} Kreditkarte";

                "Von:";"01.01.2018";
                "Bis:";"31.01.2018";
                "Saldo:";"5.000,01 EUR";
                "Datum:";"15.02.2018";

                {header};
            ''', dict(card_number=self.card_number, header=HEADER)))

        importer = CreditImporter(other_iban, 'Assets:DKB:Credit')

        with open(self.filename) as fd:
            self.assertFalse(importer.identify(fd))

    def test_extract_no_transactions(self):
        importer = CreditImporter(self.card_number, 'Assets:DKB:Credit')

        with open(self.filename, 'wb') as fd:
            fd.write(_format('''
                "Kreditkarte:";"{card_number} Kreditkarte";

                "Von:";"01.01.2018";
                "Bis:";"31.01.2018";
                "Saldo:";"5.000,01 EUR";
                "Datum:";"15.02.2018";

                {header};
            ''', dict(card_number=self.card_number, header=HEADER)))

        with open(self.filename) as fd:
            transactions = importer.extract(fd)

        self.assertEqual(len(transactions), 1)
        self.assertTrue(isinstance(transactions[0], Balance))
        self.assertEqual(transactions[0].date, datetime.date(2018, 2, 15))
        self.assertEqual(transactions[0].amount,
                         Amount(Decimal('5000.01'), currency='EUR'))

    def test_extract_transactions(self):
        with open(self.filename, 'wb') as fd:
            fd.write(_format('''
                "Kreditkarte:";"{card_number} Kreditkarte";

                "Von:";"01.01.2018";
                "Bis:";"31.01.2018";
                "Saldo:";"5.000,01 EUR";
                "Datum:";"15.02.2018";

                {header};
                "Ja";"15.01.2018";"15.01.2018";"REWE Filiale Muenchen";"-10,80";"";
            ''', dict(card_number=self.card_number, header=HEADER)))  # NOQA

        importer = CreditImporter(self.card_number, 'Assets:DKB:Credit',
                                  file_encoding='utf-8')

        with open(self.filename) as fd:
            transactions = importer.extract(fd)

        self.assertEqual(len(transactions), 2)
        self.assertEqual(transactions[0].date, datetime.date(2018, 1, 15))

        self.assertEqual(len(transactions[0].postings), 1)
        self.assertEqual(transactions[0].postings[0].account,
                         'Assets:DKB:Credit')
        self.assertEqual(transactions[0].postings[0].units.currency, 'EUR')
        self.assertEqual(transactions[0].postings[0].units.number,
                         Decimal('-10.80'))

    def test_extract_sets_timestamps(self):
        with open(self.filename, 'wb') as fd:
            fd.write(_format('''
                "Kreditkarte:";"{card_number} Kreditkarte";

                "Von:";"01.01.2018";
                "Bis:";"31.01.2018";
                "Saldo:";"5.000,01 EUR";
                "Datum:";"15.02.2018";

                {header};
                "Ja";"15.01.2018";"15.01.2018";"REWE Filiale Muenchen";"-10,80";"";
            ''', dict(card_number=self.card_number, header=HEADER)))  # NOQA

        importer = CreditImporter(self.card_number, 'Assets:DKB:Credit',
                                  file_encoding='utf-8')

        self.assertFalse(importer._date_from)
        self.assertFalse(importer._date_to)
        self.assertFalse(importer._balance)

        with open(self.filename) as fd:
            transactions = importer.extract(fd)

        self.assertTrue(transactions)
        self.assertEqual(importer._date_from, datetime.date(2018, 1, 1))
        self.assertEqual(importer._date_to, datetime.date(2018, 1, 31))
        self.assertEqual(importer._date_balance, datetime.date(2018, 2, 15))

    def test_emits_closing_balance_directive(self):
        with open(self.filename, 'wb') as fd:
            fd.write(_format('''
                "Kreditkarte:";"{card_number} Kreditkarte";

                "Von:";"01.01.2018";
                "Bis:";"31.01.2018";
                "Saldo:";"5.000,01 EUR";
                "Datum:";"15.02.2018";

                {header};
                "Ja";"15.01.2018";"15.01.2018";"REWE Filiale Muenchen";"-10,80";"";
            ''', dict(card_number=self.card_number, header=HEADER)))  # NOQA
        importer = CreditImporter(self.card_number, 'Assets:DKB:Credit',
                                  file_encoding='utf-8')


        with open(self.filename) as fd:
            transactions = importer.extract(fd)

        self.assertEqual(len(transactions), 2)
        self.assertTrue(isinstance(transactions[1], Balance))
        self.assertEqual(transactions[1].date, datetime.date(2018, 2, 15))
        self.assertEqual(transactions[1].amount,
                         Amount(Decimal('5000.01'), currency='EUR'))
