from unittest import TestCase
import os.path

from beancount.ingest.cache import _FileMemo
from beancount_dkb import ECImporter


def path_for_data_file(name):
    return os.path.join(os.getcwd(), 'tests', 'data', 'ec', name)


class ECImporterTestCase(TestCase):
    def test_identify_correct(self):
        iban = 'DE99999999999999999999'

        importer = ECImporter(iban, 'Assets:DKB:EC')

        self.assertTrue(
            importer.identify(_FileMemo(path_for_data_file('empty.csv'))))

    def test_identify_invalid_iban(self):
        iban = 'DE00000000000000000000'

        importer = ECImporter(iban, 'Assets:DKB:EC')

        self.assertFalse(
            importer.identify(_FileMemo(path_for_data_file('empty.csv'))))

    def test_extract_no_transactions(self):
        iban = 'DE99999999999999999999'

        importer = ECImporter(iban, 'Assets:DKB:EC')

        self.assertFalse(
            importer.extract(_FileMemo(path_for_data_file('empty.csv'))))
