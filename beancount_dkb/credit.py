import csv
from datetime import datetime, timedelta

from beancount.core import data
from beancount.core.amount import Amount
from beancount.core.number import Decimal
from beancount.ingest import importer

from ._common import fmt_number_de, InvalidFormatError

FIELDS = (
    'Umsatz abgerechnet und nicht im Saldo enthalten',
    'Wertstellung',
    'Belegdatum',
    'Beschreibung',
    'Betrag (EUR)',
    'Ursprünglicher Betrag',
)


class CreditImporter(importer.ImporterProtocol):
    def __init__(
        self, card_number, account, currency='EUR', file_encoding='utf-8'
    ):
        self.card_number = card_number
        self.account = account
        self.currency = currency
        self.file_encoding = file_encoding

        self._expected_headers = (
            '"Kreditkarte:";"{} Kreditkarte";'.format(self.card_number),
            '"Kreditkarte:";"{}";'.format(self.card_number),
        )

        self._date_from = None
        self._date_to = None

        # The balance amount is picked from the "Saldo" meta entry, and
        # corresponds to the amount at the end of the date contained in the
        # "Datum" meta. From the data seen so far, this date is a few days
        # behind the end of the last date, and marks the border between
        # "Gebucht" and "Vorgemerkt" transactions.
        #
        # Also, since there is no documentation on the file format, this
        # behavior is implemented purely based on intuition, but has worked out
        # OK so far.
        #
        # Beancount expects the balance amount to be from the beginning of the
        # day, while the Tagessaldo entries in the DKB exports seem to be from
        # the end of the day. So when setting the balance date, we add a
        # timedelta of 1 day to the original value to make the balance
        # assertions work.

        self._balance_date = None
        self._balance_amount = None

    def name(self):
        return 'DKB {}'.format(self.__class__.__name__)

    def file_account(self, _):
        return self.account

    def file_date(self, file_):
        self.extract(file_)

        return self._balance_date - timedelta(days=1)

    def is_valid_header(self, line):
        return any(
            line.startswith(header) for header in self._expected_headers
        )

    def identify(self, file_):
        with open(file_.name, encoding=self.file_encoding) as fd:
            line = fd.readline().strip()

        return self.is_valid_header(line)

    def extract(self, file_):
        entries = []
        line_index = 0
        closing_balance_index = -1

        with open(file_.name, encoding=self.file_encoding) as fd:
            # Header
            line = fd.readline().strip()
            line_index += 1

            if not self.is_valid_header(line):
                raise InvalidFormatError()

            # Empty line
            line = fd.readline().strip()
            line_index += 1

            if line:
                raise InvalidFormatError()

            # Meta
            expected_keys = set(['Von:', 'Bis:', 'Saldo:', 'Datum:'])

            lines = [fd.readline().strip() for _ in range(len(expected_keys))]

            reader = csv.reader(
                lines, delimiter=';', quoting=csv.QUOTE_MINIMAL, quotechar='"'
            )

            for line in reader:
                key, value, _ = line
                line_index += 1

                if key.startswith('Von'):
                    self._date_from = datetime.strptime(
                        value, '%d.%m.%Y'
                    ).date()
                elif key.startswith('Bis'):
                    self._date_to = datetime.strptime(value, '%d.%m.%Y').date()
                elif key.startswith('Saldo'):
                    self._balance_amount = Amount(
                        Decimal(value.rstrip(' EUR')), self.currency
                    )
                    closing_balance_index = line_index
                elif key.startswith('Datum'):
                    self._balance_date = datetime.strptime(
                        value, '%d.%m.%Y'
                    ).date() + timedelta(days=1)

                expected_keys.remove(key)

            if expected_keys:
                raise ValueError()

            # Another empty line
            line = fd.readline().strip()
            line_index += 1

            if line:
                raise InvalidFormatError()

            # Data entries
            reader = csv.DictReader(
                fd, delimiter=';', quoting=csv.QUOTE_MINIMAL, quotechar='"'
            )

            for index, line in enumerate(reader):
                meta = data.new_metadata(file_.name, index)

                amount = Amount(
                    fmt_number_de(line['Betrag (EUR)']), self.currency
                )

                date = datetime.strptime(line['Belegdatum'], '%d.%m.%Y').date()

                description = line['Beschreibung']

                postings = [
                    data.Posting(self.account, amount, None, None, None, None)
                ]

                entries.append(
                    data.Transaction(
                        meta,
                        date,
                        self.FLAG,
                        None,
                        description,
                        data.EMPTY_SET,
                        data.EMPTY_SET,
                        postings,
                    )
                )

            # Closing Balance
            meta = data.new_metadata(file_.name, closing_balance_index)
            entries.append(
                data.Balance(
                    meta,
                    self._balance_date,
                    self.account,
                    self._balance_amount,
                    None,
                    None,
                )
            )

        return entries
