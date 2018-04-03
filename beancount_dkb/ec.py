import csv
from datetime import datetime
import locale

from beancount.core.amount import Amount
from beancount.core import data
from beancount.core.number import Decimal
from beancount.ingest import importer

from ._common import change_locale, InvalidFormatError


FIELDS = (
    'Buchungstag',
    'Wertstellung',
    'Buchungstext',
    'Auftraggeber / Begünstigter',
    'Verwendungszweck',
    'Kontonummer',
    'BLZ',
    'Betrag (EUR)',
    'Gläubiger-ID',
    'Mandatsreferenz',
    'Kundenreferenz',
)


class ECImporter(importer.ImporterProtocol):
    def __init__(self, iban, account, currency='EUR', ignore_tagessaldo=True,
                 numeric_locale='de_DE.UTF-8', file_encoding='utf-8'):
        self.iban = iban
        self.account = account
        self.currency = currency
        self.ignore_tagessaldo = ignore_tagessaldo
        self.numeric_locale = numeric_locale
        self.file_encoding = file_encoding

        self._expected_header = \
            '"Kontonummer:";"{} / Girokonto";'.format(self.iban)
        self._date_from = None
        self._date_to = None
        self._balance = None

    def file_account(self, _):
        return self.account

    def identify(self, file_):
        with open(file_.name, encoding=self.file_encoding) as fd:
            line = fd.readline().strip()

        return line.startswith(self._expected_header)

    def extract(self, file_):
        entries = []

        def _read_header(fd):
            line = fd.readline().strip()

            if line != self._expected_header:
                raise InvalidFormatError()

        def _read_empty_line(fd):
            line = fd.readline().strip()

            if line:
                raise InvalidFormatError()

        def _read_meta(fd):
            lines = [fd.readline().strip() for _ in range(3)]

            reader = csv.reader(lines, delimiter=';',
                                quoting=csv.QUOTE_MINIMAL, quotechar='"')

            for line in reader:
                key, value, _ = line

                if key.startswith('Von'):
                    self._date_from = datetime.strptime(
                        value, '%d.%m.%Y').date()
                elif key.startswith('Bis'):
                    self._date_to = datetime.strptime(
                        value, '%d.%m.%Y').date()
                elif key.startswith('Kontostand vom'):
                    self._balance = locale.atof(value.rstrip(' EUR'), Decimal)

        with change_locale(locale.LC_NUMERIC, self.numeric_locale):
            with open(file_.name, encoding=self.file_encoding) as fd:
                # Header
                _read_header(fd)

                # Empty line
                _read_empty_line(fd)

                # Meta
                _read_meta(fd)

                # Another empty line
                _read_empty_line(fd)

                # Data entries
                reader = csv.DictReader(fd, delimiter=';',
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
