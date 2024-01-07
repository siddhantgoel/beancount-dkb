import csv
from collections import namedtuple
from datetime import date, datetime
from typing import IO, Dict

from ..exceptions import InvalidFormatError

Meta = namedtuple("Meta", ["value", "line_index"])


class BaseExtractor:
    def __init__(self, card_number: str):
        self.card_number = card_number

    def identify(self, file) -> bool:
        raise NotImplementedError()

    def extract_header(self, fd: IO):
        line = fd.readline().strip()

        if not self.matches_header(line):
            raise InvalidFormatError()

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

    HEADER = ";".join(f'"{field}"' for field in FIELDS) + ";"

    file_encoding = "ISO-8859-1"

    def identify(self, file) -> bool:
        expected_header_prefixes = (
            f'"Kreditkarte:";"{self.card_number} Kreditkarte";',
            f'"Kreditkarte:";"{self.card_number}";',
            f'"Kreditkarte:";"{self.card_number[:4]}********{self.card_number[-4:]}";',
        )

        with open(file.name, encoding=self.file_encoding) as fd:
            line = fd.readline().strip()

            return any(line.startswith(header) for header in expected_header_prefixes)

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

    HEADER = ";".join(f'"{field}"' for field in FIELDS)

    file_encoding = "utf-8-sig"

    def identify(self, file) -> bool:
        expected_header_prefix = f'"Karte";"Visa-Kreditkarte {self.card_number[:4]}'

        try:
            with open(file.name, encoding=self.file_encoding) as fd:
                line = fd.readline().strip()

                return line.startswith(expected_header_prefix)
        except UnicodeDecodeError:
            return False

    def get_amount(self, line: Dict[str, str]) -> str:
        return line["Betrag"].rstrip(" €")

    def get_valuation_date(self, line: Dict[str, str]) -> date:
        return datetime.strptime(line["Wertstellung"], "%d.%m.%y").date()

    def get_description(self, line: Dict[str, str]) -> str:
        return line["Beschreibung"]
