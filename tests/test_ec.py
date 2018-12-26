import datetime
import os
from decimal import Decimal
from tempfile import gettempdir
from textwrap import dedent
from unittest import TestCase

from beancount.core.data import Amount, Balance

from beancount_dkb import ECImporter
from beancount_dkb.ec import FIELDS

HEADER = ';'.join('"{}"'.format(field) for field in FIELDS)


def path_for_temp_file(name):
    return os.path.join(gettempdir(), name)


def _format(string, kwargs):
    return dedent(string).format(**kwargs).lstrip().encode('utf-8')


class ECImporterTestCase(TestCase):
    def setUp(self):
        super(ECImporterTestCase, self).setUp()

        self.iban = 'DE99999999999999999999'
        self.formatted_iban = 'DE99 9999 9999 9999 9999 99'
        self.filename = path_for_temp_file('{}.csv'.format(self.iban))

    def tearDown(self):
        if os.path.isfile(self.filename):
            os.remove(self.filename)

        super(ECImporterTestCase, self).tearDown()

    def test_identify_correct(self):
        importer = ECImporter(self.iban, 'Assets:DKB:EC')

        with open(self.filename, 'wb') as fd:
            fd.write(
                _format(
                    '''
                    "Kontonummer:";"{iban} / Girokonto";

                    "Von:";"01.01.2018";
                    "Bis:";"31.01.2018";
                    "Kontostand vom 31.01.2018:";"5.000,01 EUR";

                    {header};
                    ''',
                    dict(iban=self.iban, header=HEADER),
                )
            )

        with open(self.filename) as fd:
            self.assertTrue(importer.identify(fd))

    def test_identify_with_nonstandard_account_name(self):
        importer = ECImporter(self.iban, 'Assets:DKB:EC')

        with open(self.filename, 'wb') as fd:
            fd.write(
                _format(
                    '''
                    "Kontonummer:";"{iban} / My Custom Named Account";

                    "Von:";"01.01.2018";
                    "Bis:";"31.01.2018";
                    "Kontostand vom 31.01.2018:";"5.000,01 EUR";

                    {header};
                    ''',
                    dict(iban=self.iban, header=HEADER),
                )
            )

        with open(self.filename) as fd:
            self.assertTrue(importer.identify(fd))

    def test_identify_with_exotic_account_name(self):
        importer = ECImporter(self.iban, 'Assets:DKB:EC')

        with open(self.filename, 'wb') as fd:
            fd.write(
                _format(
                    '''
                    "Kontonummer:";"{iban} / Girökóntô, Γιροκοντώ, 預金, حساب البنك";

                    "Von:";"01.01.2018";
                    "Bis:";"31.01.2018";
                    "Kontostand vom 31.01.2018:";"5.000,01 EUR";

                    {header};
                    ''',  # NOQA
                    dict(iban=self.iban, header=HEADER),
                )
            )

        with open(self.filename) as fd:
            self.assertTrue(importer.identify(fd))

    def test_identify_with_formatted_iban(self):
        importer = ECImporter(self.formatted_iban, 'Assets:DKB:EC')

        with open(self.filename, 'wb') as fd:
            fd.write(
                _format(
                    '''
                    "Kontonummer:";"{iban} / Girokonto";

                    "Von:";"01.01.2018";
                    "Bis:";"31.01.2018";
                    "Kontostand vom 31.01.2018:";"5.000,01 EUR";

                    {header};
                    ''',
                    dict(iban=self.iban, header=HEADER),
                )
            )

        with open(self.filename) as fd:
            self.assertTrue(importer.identify(fd))

    def test_identify_invalid_iban(self):
        other_iban = 'DE00000000000000000000'

        with open(self.filename, 'wb') as fd:
            fd.write(
                _format(
                    '''
                    "Kontonummer:";"{iban} / Girokonto";

                    "Von:";"01.01.2018";
                    "Bis:";"31.01.2018";
                    "Kontostand vom 31.01.2018:";"5.000,01 EUR";

                    {header};
                    ''',
                    dict(iban=self.iban, header=HEADER),
                )
            )

        importer = ECImporter(other_iban, 'Assets:DKB:EC')

        with open(self.filename) as fd:
            self.assertFalse(importer.identify(fd))

    def test_extract_no_transactions(self):
        importer = ECImporter(self.iban, 'Assets:DKB:EC')

        with open(self.filename, 'wb') as fd:
            fd.write(
                _format(
                    '''
                    "Kontonummer:";"{iban} / Girokonto";

                    "Von:";"01.01.2018";
                    "Bis:";"31.01.2018";
                    "Kontostand vom 31.01.2018:";"5.000,01 EUR";

                    {header};
                    ''',
                    dict(iban=self.iban, header=HEADER),
                )
            )

        with open(self.filename) as fd:
            transactions = importer.extract(fd)

        self.assertEqual(len(transactions), 1)
        self.assertTrue(isinstance(transactions[0], Balance))
        self.assertEqual(transactions[0].date, datetime.date(2018, 1, 31))
        self.assertEqual(
            transactions[0].amount, Amount(Decimal('5000.01'), currency='EUR')
        )

    def test_extract_transactions(self):
        with open(self.filename, 'wb') as fd:
            fd.write(
                _format(
                    '''
                    "Kontonummer:";"{iban} / Girokonto";

                    "Von:";"01.01.2018";
                    "Bis:";"31.01.2018";
                    "Kontostand vom 31.01.2018:";"5.000,01 EUR";

                    {header};
                    "16.01.2018";"16.01.2018";"Lastschrift";"REWE Filialen Voll";"REWE SAGT DANKE.";"DE00000000000000000000";"AAAAAAAA";"-15,37";"000000000000000000    ";"0000000000000000000000";"";
                    ''',  # NOQA
                    dict(iban=self.iban, header=HEADER),
                )
            )

        importer = ECImporter(
            self.iban, 'Assets:DKB:EC', file_encoding='utf-8'
        )

        with open(self.filename) as fd:
            transactions = importer.extract(fd)

        self.assertEqual(len(transactions), 2)
        self.assertEqual(transactions[0].date, datetime.date(2018, 1, 16))
        self.assertEqual(transactions[0].payee, 'REWE Filialen Voll')
        self.assertEqual(
            transactions[0].narration, 'Lastschrift REWE SAGT DANKE.'
        )

        self.assertEqual(len(transactions[0].postings), 1)
        self.assertEqual(transactions[0].postings[0].account, 'Assets:DKB:EC')
        self.assertEqual(transactions[0].postings[0].units.currency, 'EUR')
        self.assertEqual(
            transactions[0].postings[0].units.number, Decimal('-15.37')
        )

    def test_extract_sets_timestamps(self):
        with open(self.filename, 'wb') as fd:
            fd.write(
                _format(
                    '''
                    "Kontonummer:";"{iban} / Girokonto";

                    "Von:";"01.01.2018";
                    "Bis:";"31.01.2018";
                    "Kontostand vom 31.01.2018:";"5.000,01 EUR";

                    {header};
                    "16.01.2018";"16.01.2018";"Lastschrift";"REWE Filialen Voll";"REWE SAGT DANKE.";"DE00000000000000000000";"AAAAAAAA";"-15,37";"000000000000000000    ";"0000000000000000000000";"";
                    ''',  # NOQA
                    dict(iban=self.iban, header=HEADER),
                )
            )

        importer = ECImporter(
            self.iban, 'Assets:DKB:EC', file_encoding='utf-8'
        )

        self.assertFalse(importer._date_from)
        self.assertFalse(importer._date_to)
        self.assertFalse(importer._balance_amount)
        self.assertFalse(importer._balance_date)

        with open(self.filename) as fd:
            transactions = importer.extract(fd)

        self.assertTrue(transactions)
        self.assertEqual(importer._date_from, datetime.date(2018, 1, 1))
        self.assertEqual(importer._date_to, datetime.date(2018, 1, 31))
        self.assertEqual(
            importer._balance_amount,
            Amount(Decimal('5000.01'), currency='EUR'),
        )
        self.assertEqual(importer._balance_date, datetime.date(2018, 1, 31))

    def test_tagessaldo_emits_balance_directive(self):
        with open(self.filename, 'wb') as fd:
            fd.write(
                _format(
                    '''
                    "Kontonummer:";"{iban} / Girokonto";

                    "Von:";"01.01.2018";
                    "Bis:";"31.01.2018";
                    "Kontostand vom 31.01.2018:";"5.000,01 EUR";

                    {header};
                    "20.01.2018";"";"";"";"Tagessaldo";"";"";"2.500,01";
                    ''',
                    dict(iban=self.iban, header=HEADER),
                )
            )
        importer = ECImporter(
            self.iban, 'Assets:DKB:EC', file_encoding='utf-8'
        )

        with open(self.filename) as fd:
            transactions = importer.extract(fd)

        self.assertEqual(len(transactions), 2)
        self.assertTrue(isinstance(transactions[0], Balance))
        self.assertEqual(transactions[0].date, datetime.date(2018, 1, 20))
        self.assertEqual(
            transactions[0].amount, Amount(Decimal('2500.01'), currency='EUR')
        )

    def test_tagessaldo_with_empty_balance_does_not_crash(self):
        with open(self.filename, 'wb') as fd:
            fd.write(
                _format(
                    '''
                    "Kontonummer:";"{iban} / Girokonto";

                    "Von:";"01.01.2018";
                    "Bis:";"31.01.2018";
                    "Kontostand vom 31.01.2018:";"5.000,01 EUR";

                    {header};
                    "20.01.2018";"";"";"";"Tagessaldo";"";"";"";
                    ''',
                    dict(iban=self.iban, header=HEADER),
                )
            )
        importer = ECImporter(
            self.iban, 'Assets:DKB:EC', file_encoding='utf-8'
        )

        with open(self.filename) as fd:
            transactions = importer.extract(fd)

        self.assertEqual(len(transactions), 1)
        self.assertTrue(isinstance(transactions[0], Balance))
        self.assertEqual(transactions[0].date, datetime.date(2018, 1, 31))
        self.assertEqual(
            transactions[0].amount, Amount(Decimal('5000.01'), currency='EUR')
        )

    def test_file_date(self):
        with open(self.filename, 'wb') as fd:
            fd.write(
                _format(
                    '''
                    "Kontonummer:";"{iban} / Girokonto";

                    "Von:";"01.01.2018";
                    "Bis:";"31.01.2018";
                    "Kontostand vom 31.01.2018:";"5.000,01 EUR";

                    {header};
                    "20.01.2018";"";"";"";"Tagessaldo";"";"";"2.500,01";
                    ''',
                    dict(iban=self.iban, header=HEADER),
                )
            )
        importer = ECImporter(
            self.iban, 'Assets:DKB:EC', file_encoding='utf-8'
        )

        with open(self.filename) as fd:
            self.assertEqual(
                importer.file_date(fd), datetime.date(2018, 1, 31)
            )

    def test_emits_closing_balance_directive(self):
        with open(self.filename, 'wb') as fd:
            fd.write(
                _format(
                    '''
                    "Kontonummer:";"{iban} / Girokonto";

                    "Von:";"01.01.2018";
                    "Bis:";"31.01.2018";
                    "Kontostand vom 31.01.2018:";"5.000,01 EUR";

                    {header};
                    "16.01.2018";"16.01.2018";"Lastschrift";"REWE Filialen Voll";"REWE SAGT DANKE.";"DE00000000000000000000";"AAAAAAAA";"-15,37";"000000000000000000    ";"0000000000000000000000";"";
                    ''',  # NOQA
                    dict(iban=self.iban, header=HEADER),
                )
            )
        importer = ECImporter(
            self.iban, 'Assets:DKB:EC', file_encoding='utf-8'
        )

        with open(self.filename) as fd:
            transactions = importer.extract(fd)

        self.assertEqual(len(transactions), 2)
        self.assertTrue(isinstance(transactions[1], Balance))
        self.assertEqual(transactions[1].date, datetime.date(2018, 1, 31))
        self.assertEqual(
            transactions[1].amount, Amount(Decimal('5000.01'), currency='EUR')
        )

    def test_mismatching_dates_in_meta(self):
        with open(self.filename, 'wb') as fd:
            fd.write(
                _format(
                    '''
                    "Kontonummer:";"{iban} / Girokonto";

                    "Von:";"01.01.2018";
                    "Bis:";"31.01.2018";
                    "Kontostand vom 31.01.2019:";"5.000,01 EUR";

                    {header};
                    "16.01.2018";"16.01.2018";"Lastschrift";"REWE Filialen Voll";"REWE SAGT DANKE.";"DE00000000000000000000";"AAAAAAAA";"-15,37";"000000000000000000    ";"0000000000000000000000";"";
                    ''',  # NOQA
                    dict(iban=self.iban, header=HEADER),
                )
            )

        importer = ECImporter(
            self.iban, 'Assets:DKB:EC', file_encoding='utf-8'
        )

        with open(self.filename) as fd:
            transactions = importer.extract(fd)

        self.assertEqual(len(transactions), 2)
        self.assertTrue(isinstance(transactions[1], Balance))
        self.assertEqual(transactions[1].date, datetime.date(2019, 1, 31))
        self.assertEqual(
            transactions[1].amount, Amount(Decimal('5000.01'), currency='EUR')
        )
