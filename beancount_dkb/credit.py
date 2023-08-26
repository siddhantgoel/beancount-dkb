import csv
from typing import Dict
from datetime import datetime, timedelta

from beancount.core import data
from beancount.core.amount import Amount
from beancount.core.number import Decimal
from beancount.ingest import importer

from .exceptions import InvalidFormatError
from .extractors.credit import V1Extractor, V2Extractor
from .helpers import AccountMatcher, fmt_number_de


class CreditImporter(importer.ImporterProtocol):
    def __init__(
        self,
        card_number,
        account,
        currency="EUR",
        file_encoding="utf-8",
        description_patterns=None,
    ):
        self.card_number = card_number
        self.account = account
        self.currency = currency
        self.file_encoding = file_encoding
        self.description_matcher = AccountMatcher(description_patterns)

        self._v1_extractor = V1Extractor(self.card_number)
        self._v2_extractor = V2Extractor(self.card_number)

        self._date_from = None
        self._date_to = None

        self._file_date = None

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
        return "DKB {}".format(self.__class__.__name__)

    def file_account(self, _):
        return self.account

    def file_date(self, file):
        self.extract(file)

        # in case the file contains start/end dates, return the end date
        # if not, then the file was based on a time period (Zeitraum), so we
        # return the date of the export instead

        return self._date_to or self._file_date

    def identify(self, file):
        with open(file.name, encoding=self.file_encoding) as fd:
            line = fd.readline().strip()

        return self._v1_extractor.matches_header(
            line
        ) or self._v2_extractor.matches_header(line)

    def extract(self, file, existing_entries=None):
        entries = []
        line_index = 0
        closing_balance_index = -1

        with open(file.name, encoding=self.file_encoding) as fd:
            extractor = self._get_extractor(fd.readline().strip())

            line_index += 1

            extractor.extract_empty_line(fd)
            line_index += 1

            # Read metadata lines until the next empty line

            meta = extractor.extract_meta(fd, line_index)
            self._update_meta(meta)
            line_index += len(meta) + 1

            # Data entries
            reader = csv.DictReader(
                fd, delimiter=";", quoting=csv.QUOTE_MINIMAL, quotechar='"'
            )

            for index, line in enumerate(reader):
                meta = data.new_metadata(file.name, index)

                amount = Amount(
                    fmt_number_de(extractor.get_amount(line)), self.currency
                )

                date = extractor.get_valuation_date(line)

                description = extractor.get_description(line)

                postings = [data.Posting(self.account, amount, None, None, None, None)]

                if self.description_matcher.account_matches(description):
                    postings.append(
                        data.Posting(
                            self.description_matcher.account_for(description),
                            None,
                            None,
                            None,
                            None,
                            None,
                        )
                    )

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
            meta = data.new_metadata(file.name, closing_balance_index)
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

    def _get_extractor(self, line: str):
        if self._v1_extractor.matches_header(line):
            return self._v1_extractor
        elif self._v2_extractor.matches_header(line):
            return self._v2_extractor

        raise InvalidFormatError()

    def _update_meta(self, meta: Dict[str, str]):
        for key, value in meta.items():
            if key.startswith("Von"):
                self._date_from = datetime.strptime(value.value, "%d.%m.%Y").date()
            elif key.startswith("Bis"):
                self._date_to = datetime.strptime(value.value, "%d.%m.%Y").date()
            elif key.startswith("Saldo"):
                self._balance_amount = Amount(
                    Decimal(value.value.rstrip(" EUR")), self.currency
                )
                closing_balance_index = value.line_index
                if key.startswith("Saldo vom"):
                    self._balance_date = datetime.strptime(
                        key.replace("Saldo vom ", "").replace(":", ""),
                        "%d.%m.%Y",
                    ).date()
            elif key.startswith("Datum"):
                self._file_date = datetime.strptime(value.value, "%d.%m.%Y").date()
                self._balance_date = self._file_date + timedelta(days=1)
