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
    Format a (possibly) German locale-formatted number like "123.456,78" to "123456.78"
    """

    if "." in value and "," in value:
        if value.index(".") < value.index(","):
            # if a period appears before a comma, assume de_DE
            return parse_decimal(value, locale="de_DE")
        else:
            # if a comma appears before a period, assume en_US
            return parse_decimal(value, locale="en_US")
    elif "," in value:
        # only commas, assume de_DE
        return parse_decimal(value, locale="de_DE")
    else:
        # only periods, assume en_US
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
