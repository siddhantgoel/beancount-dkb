import csv
import re
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
        raise NumberFormatError(f'{value} contains wrong number of decimal places')
    else:
        return num.quantize(Decimal('.01'))


def fmt_number_en(value: str) -> Decimal:
    """
    Format an en_US locale formatted number
    Use always 2 decimal digits
    """

    num = parse_decimal(value, locale="en_US")
    if num.as_tuple().exponent < -2:
        raise NumberFormatError(f'{value} contains wrong number of decimal places')
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
