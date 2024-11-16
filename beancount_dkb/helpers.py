import csv
import re
from collections import namedtuple
from functools import partial
from typing import Optional, Sequence

from babel.numbers import parse_decimal
from beancount.core.number import Decimal

csv_reader = partial(
    csv.reader, delimiter=",", quoting=csv.QUOTE_MINIMAL, quotechar='"'
)

csv_dict_reader = partial(
    csv.DictReader, delimiter=",", quoting=csv.QUOTE_MINIMAL, quotechar='"'
)

_MatcherEntry = namedtuple("_MatcherEntry", ["pattern", "account"])


Header = namedtuple("Header", ["value", "delimiter"])


def fmt_number_de(value: str) -> Decimal:
    """
    Format a de_DE locale formatted number
    """

    return parse_decimal(value, locale="de_DE")


def fmt_number_en(value: str) -> Decimal:
    """
    Format an en_US locale formatted number
    """

    return parse_decimal(value, locale="en_US")


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
