from collections import namedtuple
from datetime import datetime, timedelta
from typing import Dict

from beancount.core import data
from beancount.core.amount import Amount
from beancount.core.number import Decimal
from beancount.ingest import importer

from .exceptions import InvalidFormatError
from .extractors.credit import V1Extractor, V2Extractor
from .helpers import AccountMatcher, csv_dict_reader, csv_reader, fmt_number_de

Meta = namedtuple("Meta", ["value", "line_index"])


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

        self._v1_extractor = V1Extractor(card_number)
        self._v2_extractor = V2Extractor(card_number)

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
        self._closing_balance_index = -1

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
        return self._v1_extractor.identify(file) or self._v2_extractor.identify(file)

    def extract(self, file, existing_entries=None):
        extractor = None

        if self._v1_extractor.identify(file):
            extractor = self._v1_extractor
        elif self._v2_extractor.identify(file):
            extractor = self._v2_extractor
        else:
            raise InvalidFormatError()

        return self._extract(file, extractor)

    def _extract(self, file, extractor):
        entries = []

        with open(file.name, encoding=extractor.file_encoding) as fd:
            lines = [line.strip() for line in fd.readlines()]

        line_index = 0
        header_index = lines.index(extractor.HEADER)

        metadata_lines = lines[0:header_index]
        transaction_lines = lines[header_index:]

        # Metadata

        metadata = {}
        reader = csv_reader(metadata_lines)

        for line in reader:
            line_index += 1

            if not line or line == [""]:
                continue

            key, value, *_ = line

            metadata[key] = Meta(value, line_index)

        self._update_meta(metadata)

        # Transactions

        reader = csv_dict_reader(transaction_lines)

        for line in reader:
            line_index += 1

            meta = data.new_metadata(file.name, line_index)

            amount = Amount(fmt_number_de(extractor.get_amount(line)), self.currency)

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
        meta = data.new_metadata(file.name, self._closing_balance_index)
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
                self._closing_balance_index = value.line_index
                if key.startswith("Saldo vom"):
                    self._balance_date = datetime.strptime(
                        key.replace("Saldo vom ", "").replace(":", ""),
                        "%d.%m.%Y",
                    ).date()
            elif key.startswith("Datum"):
                self._file_date = datetime.strptime(value.value, "%d.%m.%Y").date()
                self._balance_date = self._file_date + timedelta(days=1)
