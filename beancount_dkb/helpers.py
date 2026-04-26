import csv
import re
import warnings
from functools import partial
from typing import NamedTuple, Optional, Sequence

from babel.numbers import parse_decimal, NumberFormatError
from beancount.core.number import Decimal

csv_reader = partial(
    csv.reader, delimiter=",", quoting=csv.QUOTE_MINIMAL, quotechar='"'
)

csv_dict_reader = partial(
    csv.DictReader, delimiter=",", quoting=csv.QUOTE_MINIMAL, quotechar='"'
)


class _MatcherEntry(NamedTuple):
    pattern: re.Pattern
    account: str


class _IBANMatcherEntry(NamedTuple):
    iban: str
    account: str


class Header(NamedTuple):
    value: str
    delimiter: str


class Meta(NamedTuple):
    value: str
    line_index: int


def fmt_number_de(value: str) -> Decimal:
    """
    Format a de_DE locale formatted number
    Use always 2 decimal digits
    """

    num = parse_decimal(value, locale="de_DE")
    if num.as_tuple().exponent < -2:
        raise NumberFormatError(f'{value} contains unexpected number of decimal places')
    else:
        return num.quantize(Decimal('.01'))


def fmt_number_en(value: str) -> Decimal:
    """
    Format an en_US locale formatted number
    Use always 2 decimal digits
    """

    num = parse_decimal(value, locale="en_US")
    if num.as_tuple().exponent < -2:
        raise NumberFormatError(f'{value} contains unexpected number of decimal places')
    else:
        return num.quantize(Decimal('.01'))


class AccountMatcher:
    def __init__(self, patterns: Optional[Sequence] = None):
        self.patterns = []

        if patterns is not None:
            for regex, account in patterns:
                self.add(regex, account)

    def add(self, regex: str, account: str) -> None:
        self.patterns.append(_MatcherEntry(re.compile(regex), account))

    def account_for(self, string: str) -> Optional[str]:
        for pattern, account in self.patterns:
            if re.search(pattern, string):
                return account

    def account_matches(self, string: str) -> bool:
        return bool(self.account_for(string))


def _normalize_iban(value: Optional[str]) -> str:
    if value is None:
        return ""

    return re.sub(r"\s+", "", value, flags=re.UNICODE).upper()


class IBANMatcher:
    def __init__(self, entries: Optional[Sequence] = None):
        self.entries = []

        if entries is not None:
            for iban, account in entries:
                self.add(iban, account)

    def add(self, iban: Optional[str], account: str) -> None:
        normalized_iban = _normalize_iban(iban)

        if not normalized_iban:
            warnings.warn(
                f"Ignoring empty iban_matcher entry for account {account}.",
            )
            return

        self.entries.append(_IBANMatcherEntry(normalized_iban, account))

    def account_for(self, value: Optional[str]) -> Optional[str]:
        normalized_iban = _normalize_iban(value)

        if not normalized_iban:
            return None

        for iban, account in self.entries:
            if iban == normalized_iban:
                return account

    def account_matches(self, value: Optional[str]) -> bool:
        return bool(self.account_for(value))
