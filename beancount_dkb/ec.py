import warnings
from collections import namedtuple
from datetime import datetime, timedelta
from functools import partial
from textwrap import dedent
from typing import Dict, Optional, Sequence

from beancount.core import data, flags
from beancount.core.amount import Amount
from beangulp.importer import Importer

from .exceptions import InvalidFormatError
from .extractors.ec import V1Extractor, V2Extractor
from .helpers import AccountMatcher, fmt_number_de

Meta = namedtuple("Meta", ["value", "line_index"])

new_posting = partial(data.Posting, cost=None, price=None, flag=None, meta=None)


class ECImporter(Importer):
    def __init__(
        self,
        iban: str,
        account_name: str,
        currency: str = "EUR",
        file_encoding: Optional[str] = None,
        meta_code: Optional[str] = None,
        payee_patterns: Optional[Sequence] = None,
        description_patterns: Optional[Sequence] = None,
    ):
        self.iban = iban
        self.account_name = account_name
        self.currency = currency
        self.meta_code = meta_code
        self.payee_matcher = AccountMatcher(payee_patterns)
        self.description_matcher = AccountMatcher(description_patterns)

        self._v1_extractor = V1Extractor(iban, meta_code)
        self._v2_extractor = V2Extractor(iban, meta_code)

        self._date_from = None
        self._date_to = None
        self._balance_amount = None
        self._balance_date = None
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

        return self._date_to

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

            amount = None
            if extractor.get_amount(line):
                amount = Amount(
                    fmt_number_de(extractor.get_amount(line)), self.currency
                )

            date = extractor.get_booking_date(line)

            if extractor.get_purpose(line) == "Tagessaldo":
                if amount:
                    entries.append(
                        data.Balance(
                            meta,
                            date + timedelta(days=1),
                            self.account(filepath),
                            amount,
                            None,
                            None,
                        )
                    )
            else:
                if self.meta_code:
                    meta[self.meta_code] = extractor.get_booking_text(line)

                description = extractor.get_description(line)
                payee = extractor.get_payee(line)

                postings = [
                    new_posting(account=self.account(filepath), units=amount),
                ]

                payee_match = self.payee_matcher.account_matches(payee)
                description_match = self.description_matcher.account_matches(
                    description
                )

                if payee_match and description_match:
                    warnings.warn(
                        f"Line {line_index + 1} matches both payee_patterns and "
                        "description_patterns. Picking payee_pattern.",
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
                            account=self.description_matcher.account_for(description),
                            units=None,
                        )
                    )

                entries.append(
                    data.Transaction(
                        meta,
                        date,
                        flags.FLAG_OKAY,
                        payee,
                        description,
                        data.EMPTY_SET,
                        data.EMPTY_SET,
                        postings,
                    )
                )

        # Closing Balance
        entries.append(
            data.Balance(
                data.new_metadata(filepath, self._closing_balance_index),
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
            elif key.startswith("Kontostand vom"):
                # Beancount expects the balance amount to be from the
                # beginning of the day, while the Tagessaldo entries in
                # the DKB exports seem to be from the end of the day.
                # So when setting the balance date, we add a timedelta
                # of 1 day to the original value to make the balance
                # assertions work.

                self._balance_amount = Amount(
                    fmt_number_de(value.value.split()[0]), self.currency
                )
                self._balance_date = datetime.strptime(
                    key.lstrip("Kontostand vom ").rstrip(":"), "%d.%m.%Y"
                ).date() + timedelta(days=1)
                self._closing_balance_index = value.line_index
