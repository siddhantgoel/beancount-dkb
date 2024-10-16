import csv
import re
from collections import namedtuple
from functools import partial
from typing import Optional, Sequence

from beancount.core.number import Decimal

csv_reader = partial(
    csv.reader, delimiter=",", quoting=csv.QUOTE_MINIMAL, quotechar='"'
)

csv_dict_reader = partial(
    csv.DictReader, delimiter=",", quoting=csv.QUOTE_MINIMAL, quotechar='"'
)

_MatcherEntry = namedtuple("_MatcherEntry", ["pattern", "account"])


def fmt_number_de(value: str) -> Decimal:
    thousands_sep = "."
    decimal_sep = ","

    return Decimal(value.replace(thousands_sep, "").replace(decimal_sep, "."))


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
