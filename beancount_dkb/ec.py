import csv
from datetime import datetime
import locale
import re

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
    def __init__(self, iban, account, currency='EUR',
                 numeric_locale='de_DE.UTF-8', file_encoding='utf-8'):
        self.account = account
        self.currency = currency
        self.numeric_locale = numeric_locale
        self.file_encoding = file_encoding

        self._expected_header_regex = re.compile(
            r"^\"Kontonummer:\";\"" +
            re.escape(re.sub(r"\s+", "", iban, flags=re.UNICODE)) + "\s",
            re.IGNORECASE
        )
        self._date_from = None
        self._date_to = None
        self._balance = None

    def file_account(self, _):
        return self.account

    def file_date(self, file_):
        self.extract(file_)
        return self._date_to

    def identify(self, file_):
        with open(file_.name, encoding=self.file_encoding) as fd:
            line = fd.readline().strip()

        return self._expected_header_regex.match(line)

    def extract(self, file_):
        entries = []

        def _read_header(fd):
            line = fd.readline().strip()

            if not self._expected_header_regex.match(line):
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
                    self._balance = Amount(locale.atof(value.rstrip(' EUR'),
                                           Decimal), self.currency)

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

                    amount = Amount(locale.atof(line['Betrag (EUR)'], Decimal),
                                    self.currency)
                    date = datetime.strptime(
                        line['Buchungstag'], '%d.%m.%Y').date()

                    if line['Verwendungszweck'] == 'Tagessaldo':
                        entries.append(
                            data.Balance(meta, date, self.account, amount,
                                         None, None)
                        )
                    else:
                        description = '{} {}'.format(
                            line['Buchungstext'],
                            line['Verwendungszweck']
                        )

                        postings = [
                            data.Posting(self.account, amount, None, None,
                                         None, None)
                        ]

                        entries.append(
                            data.Transaction(
                                meta, date, self.FLAG,
                                line['Auftraggeber / Begünstigter'],
                                description, data.EMPTY_SET, data.EMPTY_SET,
                                postings
                            )
                        )

                # Closing Balance
                meta = data.new_metadata(file_.name, 0)
                entries.append(
                    data.Balance(meta, self._date_to, self.account,
                                 self._balance, None, None)
                )

            return entries
