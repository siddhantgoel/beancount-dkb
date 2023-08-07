import csv
from collections import namedtuple
import re
from typing import Optional, IO

from .helpers import InvalidFormatError


Meta = namedtuple("Meta", ["value", "line_index"])


class BaseExtractor:
    def matches_header(self, line: str) -> bool:
        raise NotImplementedError()

    def is_empty_line(self, fd: IO) -> bool:
        raise NotImplementedError()

    def parse_amount(self, line: dict[str, str]) -> str:
        raise NotImplementedError()

    def extract_header(self, fd: IO):
        line = fd.readline().strip()

        if not self.matches_header(line):
            raise InvalidFormatError()

    def extract_empty_line(self, fd: IO):
        line = fd.readline().strip()

        if not self.is_empty_line(line):
            raise InvalidFormatError("Expected empty line")

    def extract_meta(self, fd: IO, line_index: int) -> dict[str, str]:
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
            key, value, _ = line

            meta[key] = Meta(value, line_index + index)

        return meta


class V1Extractor(BaseExtractor):
    """Extractor for DKB online banking interface available before 2023"""

    FIELDS = (
        "Buchungstag",
        "Wertstellung",
        "Buchungstext",
        "Auftraggeber / Begünstigter",
        "Verwendungszweck",
        "Kontonummer",
        "BLZ",
        "Betrag (EUR)",
        "Gläubiger-ID",
        "Mandatsreferenz",
        "Kundenreferenz",
    )

    def __init__(self, iban: str, meta_code: Optional[str] = None):
        self._expected_header_regex = re.compile(
            r'^"Kontonummer:";"'
            + re.escape(re.sub(r"\s+", "", iban, flags=re.UNICODE))
            + r"\s",
            re.IGNORECASE,
        )
        self.meta_code = meta_code

    def matches_header(self, line: str) -> bool:
        return self._expected_header_regex.match(line)

    def is_empty_line(self, line: str) -> bool:
        return line == ""

    def parse_amount(self, line: dict[str, str]) -> str:
        return line["Betrag (EUR)"]

    def parse_purpose(self, line: dict[str, str]) -> str:
        return line["Verwendungszweck"]

    def parse_account_number(self, line: dict[str, str]) -> str:
        return line["Kontonummer"]

    def parse_booking_text(self, line: dict[str, str]) -> str:
        return line["Buchungstext"]

    def parse_booking_date(self, line: dict[str, str]) -> str:
        return line["Buchungstag"]

    def parse_description(self, line: dict[str, str]) -> str:
        purpose = self.parse_purpose(line) or self.parse_account_number(line)
        booking_text = self.parse_booking_text(line)

        return f"{booking_text} {purpose}" if not self.meta_code else purpose

    def parse_payee(self, line: dict[str, str]) -> str:
        return line["Auftraggeber / Begünstigter"]


class V2Extractor(BaseExtractor):
    """Extractor for DKB online banking interface introduced in 2023"""

    FIELDS = (
        "Buchungsdatum",
        "Wertstellung",
        "Status",
        "Zahlungspflichtige*r",
        "Zahlungsempfänger*in",
        "Verwendungszweck",
        "Umsatztyp",
        "Betrag",
        "Gläubiger-ID",
        "Mandatsreferenz",
        "Kundenreferenz",
    )

    def __init__(self, iban: str, meta_code: Optional[str] = None):
        self._expected_header_regex = re.compile(
            r'^"Konto:";"Girokonto '
            + re.escape(re.sub(r"\s+", "", iban, flags=re.UNICODE)),
            re.IGNORECASE,
        )
        self.meta_code = meta_code

    def matches_header(self, line: str) -> bool:
        return self._expected_header_regex.match(line)

    def is_empty_line(self, line: str) -> bool:
        return line == '""'
