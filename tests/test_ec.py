from decimal import Decimal
from unittest import TestCase
import datetime
import os.path

from beancount_dkb import ECImporter


def path_for_data_file(name):
    return os.path.join(os.getcwd(), 'tests', 'data', 'ec', name)


class ECImporterTestCase(TestCase):
    def test_identify_correct(self):
        iban = 'DE99999999999999999999'

        importer = ECImporter(iban, 'Assets:DKB:EC')

        with open(path_for_data_file('empty.csv')) as fd:
            self.assertTrue(importer.identify(fd))

    def test_identify_invalid_iban(self):
        iban = 'DE00000000000000000000'

        importer = ECImporter(iban, 'Assets:DKB:EC')

        with open(path_for_data_file('empty.csv')) as fd:
            self.assertFalse(importer.identify(fd))

    def test_extract_no_transactions(self):
        iban = 'DE99999999999999999999'

        importer = ECImporter(iban, 'Assets:DKB:EC')

        with open(path_for_data_file('empty.csv')) as fd:
            self.assertFalse(importer.extract(fd))

    def test_extract_transactions(self):
        iban = 'DE99999999999999999999'

        importer = ECImporter(iban, 'Assets:DKB:EC')

        with open(path_for_data_file('non_empty.csv')) as fd:
            transactions = importer.extract(fd)

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].date, datetime.date(2018, 1, 16))

        self.assertEqual(len(transactions[0].postings), 1)
        self.assertEqual(transactions[0].postings[0].account, 'Assets:DKB:EC')
        self.assertEqual(transactions[0].postings[0].units.currency, 'EUR')
        self.assertEqual(transactions[0].postings[0].units.number,
                         Decimal('-15.37'))
