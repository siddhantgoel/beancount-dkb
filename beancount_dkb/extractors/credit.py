from datetime import date, datetime
from collections import namedtuple
import csv
from typing import Dict, IO

from ..exceptions import InvalidFormatError


Meta = namedtuple("Meta", ["value", "line_index"])


class BaseExtractor:
    def matches_header(self, line: str) -> bool:
        """Return true if the line matches the expected header for this extractor"""

        raise NotImplementedError()

    def is_empty_line(self, fd: IO) -> bool:
        """Return true if the line is an empty line"""

        raise NotImplementedError()

    def extract_header(self, fd: IO):
        line = fd.readline().strip()

        if not self.matches_header(line):
            raise InvalidFormatError()

    def extract_empty_line(self, fd: IO):
        line = fd.readline().strip()

        if not self.is_empty_line(line):
            raise InvalidFormatError("Expected empty line")

    def extract_meta(self, fd: IO, line_index: int) -> Dict[str, Meta]:
        lines = []

        for line in fd:
            if self.is_empty_line(line.strip()):
                break
            lines.append(line)

        meta = {}
        reader = csv.reader(
            lines, delimiter=";", quoting=csv.QUOTE_MINIMAL, quotechar='"'
        )

        for index, line in enumerate(reader):
            key, value, *_ = line

            meta[key] = Meta(value, line_index + index)

        return meta

    def get_amount(self, line: Dict[str, str]) -> str:
        raise NotImplementedError()

    def get_valuation_date(self, line: Dict[str, str]) -> date:
        raise NotImplementedError()

    def get_description(self, line: Dict[str, str]) -> str:
        raise NotImplementedError()


class V1Extractor(BaseExtractor):
    """Extractor for DKB online banking interface available before 2023"""

    FIELDS = (
        "Umsatz abgerechnet und nicht im Saldo enthalten",
        "Wertstellung",
        "Belegdatum",
        "Beschreibung",
        "Betrag (EUR)",
        "Ursprünglicher Betrag",
    )

    def __init__(self, card_number: str):
        self._expected_header_prefixes = (
            '"Kreditkarte:";"{} Kreditkarte";'.format(card_number),
            '"Kreditkarte:";"{}";'.format(card_number),
            f'"Kreditkarte:";"{card_number[:4]}********{card_number[-4:]}";',
        )

    def is_empty_line(self, line: str) -> bool:
        return line == ""

    def matches_header(self, line: str) -> bool:
        return any(line.startswith(header) for header in self._expected_header_prefixes)

    def get_amount(self, line: Dict[str, str]) -> str:
        return line["Betrag (EUR)"]

    def get_valuation_date(self, line: Dict[str, str]) -> date:
        return datetime.strptime(line["Wertstellung"], "%d.%m.%Y").date()

    def get_description(self, line: Dict[str, str]) -> str:
        return line["Beschreibung"]


class V2Extractor(BaseExtractor):
    """Extractor for DKB online banking interface available before 2023"""

    FIELDS = (
        "Belegdatum",
        "Wertstellung",
        "Status",
        "Beschreibung",
        "Umsatztyp",
        "Betrag",
        "Fremdwährungsbetrag",
    )

    def __init__(self, card_number: str):
        self._expected_header_prefix = f'"Karte";"Visa-Kreditkarte {card_number[:4]}'

    def is_empty_line(self, line: str) -> bool:
        return line == '""'

    def matches_header(self, line: str) -> bool:
        return line.startswith(self._expected_header_prefix)

    def get_amount(self, line: Dict[str, str]) -> str:
        return line["Betrag"].rstrip(" €")

    def get_valuation_date(self, line: Dict[str, str]) -> date:
        return datetime.strptime(line["Wertstellung"], "%d.%m.%y").date()

    def get_description(self, line: Dict[str, str]) -> str:
        return line["Beschreibung"]
