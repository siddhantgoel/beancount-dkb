import csv
from datetime import datetime
import locale

from beancount.core.amount import Amount
from beancount.core import data
from beancount.core.number import Decimal
from beancount.ingest import importer

from ._helpers import change_locale


class ECImporter(importer.ImporterProtocol):
    def __init__(self, iban, account, currency='EUR', ignore_tagessaldo=True,
                 numeric_locale='de_DE.UTF-8', file_encoding='ISO-8859-1'):
        self.iban = iban
        self.account = account
        self.currency = currency
        self.ignore_tagessaldo = ignore_tagessaldo
        self.numeric_locale = numeric_locale
        self.file_encoding = file_encoding

    def file_account(self, _):
        return self.account

    def identify(self, file_):
        header = '"Kontonummer:";"{} / Girokonto";'.format(self.iban)

        return file_.head().startswith(header)

    def extract(self, file_):
        entries = []

        with change_locale(locale.LC_NUMERIC, self.numeric_locale):
            with open(file_.name, self.file_encoding) as fd:
                lines = [line for index, line in enumerate(fd)
                         if index >= 6]

                reader = csv.DictReader(lines, delimiter=';',
                                        quoting=csv.QUOTE_MINIMAL,
                                        quotechar='"')

                for index, line in enumerate(reader):
                    meta = data.new_metadata(file_.name, index)

                    if self.ignore_tagessaldo and \
                            line['Verwendungszweck'] == 'Tagessaldo':
                        continue

                    amount = Amount(locale.atof(line['Betrag (EUR)'], Decimal),
                                    self.currency)

                    date = datetime.strptime(
                        line['Buchungstag'], '%d.%m.%Y').date()

                    description = '{} {}'.format(
                        line['Buchungstext'],
                        line['Auftraggeber / Begünstigter']
                    )

                    postings = [
                        data.Posting(self.account, amount, None, None, None,
                                     None)
                    ]

                    entries.append(
                        data.Transaction(meta, date, self.FLAG, None,
                                         description, data.EMPTY_SET,
                                         data.EMPTY_SET, postings)
                    )

            return entries
