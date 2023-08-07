import csv
import re
from datetime import datetime, timedelta
from typing import Optional, Sequence, IO
from functools import partial
import warnings

from beancount.core import data
from beancount.core.amount import Amount
from beancount.ingest import importer

from .helpers import AccountMatcher, fmt_number_de, InvalidFormatError
from .extractors import V1Extractor, V2Extractor


new_posting = partial(data.Posting, cost=None, price=None, flag=None, meta=None)


class ECImporter(importer.ImporterProtocol):
    def __init__(
        self,
        iban: str,
        account: str,
        currency: str = "EUR",
        file_encoding: str = "utf-8",
        meta_code: Optional[str] = None,
        payee_patterns: Optional[Sequence] = None,
        description_patterns: Optional[Sequence] = None,
    ):
        self.iban = iban
        self.account = account
        self.currency = currency
        self.file_encoding = file_encoding
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
        with open(file.name, encoding=self.file_encoding) as fd:
            line = fd.readline().strip()

        return self._v1_extractor.matches_header(
            line
        ) or self._v2_extractor.matches_header(line)

    def extract(self, file, existing_entries=None):
        entries = []
        line_index = 0

        with open(file.name, encoding=self.file_encoding) as fd:
            extractor = self._get_extractor(fd.readline().strip())

            line_index += 1

            # empty line

            extractor.extract_empty_line(fd)
            line_index += 1

            # Read metadata lines until the next empty line

            meta = extractor.extract_meta(fd, line_index)
            self._update_meta(meta)
            line_index += 1 + len(meta)

            # Data entries
            reader = csv.DictReader(
                fd, delimiter=";", quoting=csv.QUOTE_MINIMAL, quotechar='"'
            )

            for line in reader:
                line_index += 1

                meta = data.new_metadata(file.name, line_index)

                amount = None
                if extractor.parse_amount(line):
                    amount = Amount(
                        fmt_number_de(extractor.parse_amount(line)), self.currency
                    )

                date = datetime.strptime(
                    extractor.parse_booking_date(line), "%d.%m.%Y"
                ).date()

                if extractor.parse_purpose(line) == "Tagessaldo":
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
                        meta[self.meta_code] = extractor.parse_booking_text(line)

                    description = extractor.parse_description(line)
                    payee = extractor.parse_payee(line)

                    postings = [
                        new_posting(account=self.account, units=amount),
                    ]

                    payee_match = self.payee_matcher.account_matches(payee)
                    description_match = self.description_matcher.account_matches(
                        description
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

    def _get_extractor(self, line: str):
        if self._v1_extractor.matches_header(line):
            return self._v1_extractor
        elif self._v2_extractor.matches_header(line):
            return self._v2_extractor

        raise InvalidFormatError()

    def _update_meta(self, meta: dict[str, str]):
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
