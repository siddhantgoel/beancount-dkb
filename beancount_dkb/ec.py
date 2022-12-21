import csv
import re
from datetime import datetime, timedelta
from typing import Optional, Sequence
from functools import partial
import warnings

from beancount.core import data
from beancount.core.amount import Amount
from beancount.ingest import importer

from .helpers import AccountMatcher, fmt_number_de, InvalidFormatError


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


new_posting = partial(
    data.Posting, cost=None, price=None, flag=None, meta=None
)


class ECImporter(importer.ImporterProtocol):
    def __init__(
        self,
        iban: str,
        account: str,
        currency: str = 'EUR',
        file_encoding: str = 'utf-8',
        meta_code: Optional[str] = None,
        payee_patterns: Optional[Sequence] = None,
        description_patterns: Optional[Sequence] = None,
    ):
        self.account = account
        self.currency = currency
        self.file_encoding = file_encoding
        self.meta_code = meta_code
        self.payee_matcher = AccountMatcher(payee_patterns)
        self.description_matcher = AccountMatcher(description_patterns)

        self._expected_header_regex = re.compile(
            r'^"Kontonummer:";"'
            + re.escape(re.sub(r'\s+', '', iban, flags=re.UNICODE))
            + r'\s',
            re.IGNORECASE,
        )
        self._date_from = None
        self._date_to = None
        self._balance_amount = None
        self._balance_date = None

    def name(self):
        return 'DKB {}'.format(self.__class__.__name__)

    def file_account(self, _):
        return self.account

    def file_date(self, file_):
        self.extract(file_)

        return self._date_to

    def identify(self, file_):
        with open(file_.name, encoding=self.file_encoding) as fd:
            line = fd.readline().strip()

        return self._expected_header_regex.match(line)

    def extract(self, file_, existing_entries=None):
        entries = []
        line_index = 0
        closing_balance_index = -1

        with open(file_.name, encoding=self.file_encoding) as fd:
            self._extract_header(fd)
            line_index += 1

            self._extract_empty_line(fd)
            line_index += 1

            # Meta
            lines = [fd.readline().strip() for _ in range(3)]

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
                elif key.startswith('Kontostand vom'):
                    # Beancount expects the balance amount to be from the
                    # beginning of the day, while the Tagessaldo entries in
                    # the DKB exports seem to be from the end of the day.
                    # So when setting the balance date, we add a timedelta
                    # of 1 day to the original value to make the balance
                    # assertions work.

                    self._balance_amount = Amount(
                        fmt_number_de(value.rstrip(' EUR')), self.currency
                    )
                    self._balance_date = datetime.strptime(
                        key.lstrip('Kontostand vom ').rstrip(':'), '%d.%m.%Y'
                    ).date() + timedelta(days=1)
                    closing_balance_index = line_index

            self._extract_empty_line(fd)
            line_index += 1

            # Data entries
            reader = csv.DictReader(
                fd, delimiter=';', quoting=csv.QUOTE_MINIMAL, quotechar='"'
            )

            for line in reader:
                line_index += 1

                meta = data.new_metadata(file_.name, line_index)

                amount = None
                if line['Betrag (EUR)']:
                    amount = Amount(
                        fmt_number_de(line['Betrag (EUR)']), self.currency
                    )
                date = datetime.strptime(
                    line['Buchungstag'], '%d.%m.%Y'
                ).date()

                if line['Verwendungszweck'] == 'Tagessaldo':
                    if amount:
                        entries.append(
                            data.Balance(
                                meta,
                                date + timedelta(days=1),
                                self.account,
                                amount,
                                None,
                                None,
                            )
                        )
                else:
                    verwendungszweck = (
                        line['Verwendungszweck'] or line['Kontonummer']
                    )
                    buchungstext = line['Buchungstext']
                    payee = line['Auftraggeber / Begünstigter']

                    if self.meta_code:
                        meta[self.meta_code] = buchungstext
                        description = verwendungszweck
                    else:
                        description = '{} {}'.format(
                            buchungstext,
                            verwendungszweck,
                        )

                    postings = [
                        new_posting(account=self.account, units=amount),
                    ]

                    payee_match = self.payee_matcher.account_matches(payee)
                    description_match = (
                        self.description_matcher.account_matches(description)
                    )

                    if payee_match and description_match:
                        warnings.warn(
                            f"Line {line_index + 1} matches both "
                            "payee_patterns and description_patterns. "
                            "Picking payee_pattern.",
                        )
                        postings.append(
                            new_posting(
                                account=self.payee_matcher.account_for(payee),
                                units=None,
                            )
                        )
                    elif payee_match:
                        postings.append(
                            new_posting(
                                account=self.payee_matcher.account_for(payee),
                                units=None,
                            )
                        )
                    elif description_match:
                        postings.append(
                            new_posting(
                                account=self.description_matcher.account_for(
                                    description
                                ),
                                units=None,
                            )
                        )

                    entries.append(
                        data.Transaction(
                            meta,
                            date,
                            self.FLAG,
                            payee,
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

    def _extract_header(self, fd):
        line = fd.readline().strip()

        if not self._expected_header_regex.match(line):
            raise InvalidFormatError()

    def _extract_empty_line(self, fd):
        line = fd.readline().strip()

        if line:
            raise InvalidFormatError()
