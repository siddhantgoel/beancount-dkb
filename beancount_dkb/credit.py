import warnings
from collections import namedtuple
from datetime import datetime, timedelta
from textwrap import dedent
from typing import Dict, Optional, Sequence

from beancount.core import data, flags
from beancount.core.amount import Amount
from beancount.core.number import Decimal
from beangulp.importer import Importer

from .exceptions import InvalidFormatError
from .extractors.credit import V1Extractor, V2Extractor
from .helpers import AccountMatcher, fmt_number_de, fmt_number_en

Meta = namedtuple("Meta", ["value", "line_index"])


class CreditImporter(Importer):
    def __init__(
        self,
        card_number: str,
        account_name: str,
        currency: Optional[str] = "EUR",
        file_encoding: Optional[str] = None,
        description_patterns: Optional[Sequence] = None,
    ):
        self.card_number = card_number
        self.account_name = account_name
        self.currency = currency
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

        if file_encoding is not None:
            warnings.warn(
                dedent(
                    """
                    The file_encoding parameter is no longer being used and will be
                    removed in a future version.
                    """
                ),
                DeprecationWarning,
            )

    @property
    def name(self):
        return "DKB {}".format(self.__class__.__name__)

    def account(self, filepath: str) -> data.Account:
        return self.account_name

    def date(self, filepath: str):
        self.extract(filepath, existing=None)

        # in case the file contains start/end dates, return the end date
        # if not, then the file was based on a time period (Zeitraum), so we
        # return the date of the export instead

        return self._date_to or self._file_date

    def identify(self, filepath: str):
        self._v1_extractor.set_filepath(filepath)
        self._v2_extractor.set_filepath(filepath)

        return self._v1_extractor.identify() or self._v2_extractor.identify()

    def extract(self, filepath: str, existing: Optional[data.Entries] = None):
        existing = existing or []

        self._v1_extractor.set_filepath(filepath)
        self._v2_extractor.set_filepath(filepath)

        extractor = None

        if self._v1_extractor.identify():
            extractor = self._v1_extractor
        elif self._v2_extractor.identify():
            extractor = self._v2_extractor
        else:
            raise InvalidFormatError()

        return self._extract(filepath, extractor) + existing

    def _extract(self, filepath, extractor):
        entries = []

        line_index = 0

        metadata_lines = extractor.extract_metadata_lines()
        transaction_lines = extractor.extract_transaction_lines()

        # Metadata

        metadata = {}
        reader = extractor.csv_reader(metadata_lines)

        for line in reader:
            line_index += 1

            if not line or line == [""]:
                continue

            key, value, *_ = line

            metadata[key] = Meta(value, line_index)

        self._update_meta(metadata)

        # Transactions

        reader = extractor.csv_dict_reader(transaction_lines)

        for line in reader:
            line_index += 1

            meta = data.new_metadata(filepath, line_index)

            amount = Amount(fmt_number_de(extractor.get_amount(line)), self.currency)

            date = extractor.get_valuation_date(line)

            description = extractor.get_description(line)

            postings = [
                data.Posting(self.account(filepath), amount, None, None, None, None)
            ]

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
                    flags.FLAG_OKAY,
                    None,
                    description,
                    data.EMPTY_SET,
                    data.EMPTY_SET,
                    postings,
                )
            )

        # Closing Balance
        meta = data.new_metadata(filepath, self._closing_balance_index)
        entries.append(
            data.Balance(
                meta,
                self._balance_date,
                self.account(filepath),
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
                amount = value.value
                if amount.startswith("--"):
                    amount = value.value.lstrip("--")

                self._balance_amount = Amount(
                    Decimal(fmt_number_en(amount.rstrip(" EUR"))), self.currency
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
