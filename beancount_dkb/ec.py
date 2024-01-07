import warnings
from collections import namedtuple
from datetime import datetime, timedelta
from functools import partial
from typing import Dict, Optional, Sequence

from beancount.core import data
from beancount.core.amount import Amount
from beancount.ingest import importer

from .exceptions import InvalidFormatError
from .extractors.ec import V1Extractor, V2Extractor
from .helpers import AccountMatcher, csv_dict_reader, csv_reader, fmt_number_de

Meta = namedtuple("Meta", ["value", "line_index"])

new_posting = partial(data.Posting, cost=None, price=None, flag=None, meta=None)


class ECImporter(importer.ImporterProtocol):
    def __init__(
        self,
        iban: str,
        account: str,
        currency: str = "EUR",
        meta_code: Optional[str] = None,
        payee_patterns: Optional[Sequence] = None,
        description_patterns: Optional[Sequence] = None,
    ):
        self.iban = iban
        self.account = account
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

    def name(self):
        return "DKB {}".format(self.__class__.__name__)

    def file_account(self, _):
        return self.account

    def file_date(self, file):
        self.extract(file)

        return self._date_to

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
                            self.account,
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
                    new_posting(account=self.account, units=amount),
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
                        self.FLAG,
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
                data.new_metadata(file.name, self._closing_balance_index),
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
            elif key.startswith("Kontostand vom"):
                # Beancount expects the balance amount to be from the
                # beginning of the day, while the Tagessaldo entries in
                # the DKB exports seem to be from the end of the day.
                # So when setting the balance date, we add a timedelta
                # of 1 day to the original value to make the balance
                # assertions work.

                self._balance_amount = Amount(
                    fmt_number_de(value.value.rstrip(" EUR")), self.currency
                )
                self._balance_date = datetime.strptime(
                    key.lstrip("Kontostand vom ").rstrip(":"), "%d.%m.%Y"
                ).date() + timedelta(days=1)
                self._closing_balance_index = value.line_index
