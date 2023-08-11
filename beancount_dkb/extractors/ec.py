from datetime import date, datetime
import csv
from collections import namedtuple
import re
from typing import Optional, IO, Dict

from ..helpers import InvalidFormatError


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

    def extract_meta(self, fd: IO, line_index: int) -> Dict[str, str]:
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

    def get_account_number(self, line: Dict[str, str]) -> str:
        raise NotImplementedError()

    def get_amount(self, line: Dict[str, str]) -> str:
        raise NotImplementedError()

    def get_booking_date(self, line: Dict[str, str]) -> str:
        raise NotImplementedError()

    def get_booking_text(self, line: Dict[str, str]) -> str:
        raise NotImplementedError()

    def get_description(self, line: Dict[str, str]) -> str:
        raise NotImplementedError()

    def get_payee(self, line: Dict[str, str]) -> str:
        raise NotImplementedError()

    def get_purpose(self, line: Dict[str, str]) -> str:
        raise NotImplementedError()


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

    def get_account_number(self, line: Dict[str, str]) -> str:
        return line["Kontonummer"]

    def get_amount(self, line: Dict[str, str]) -> str:
        return line["Betrag (EUR)"]

    def get_booking_date(self, line: Dict[str, str]) -> date:
        return datetime.strptime(line["Buchungstag"], "%d.%m.%Y").date()

    def get_booking_text(self, line: Dict[str, str]) -> str:
        return line["Buchungstext"]

    def get_description(self, line: Dict[str, str]) -> str:
        purpose = self.get_purpose(line) or self.get_account_number(line)
        booking_text = self.get_booking_text(line)

        return f"{booking_text} {purpose}" if not self.meta_code else purpose

    def get_payee(self, line: Dict[str, str]) -> str:
        return line["Auftraggeber / Begünstigter"]

    def get_purpose(self, line: Dict[str, str]) -> str:
        return line["Verwendungszweck"]


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
            r'^"Konto";"Girokonto '
            + re.escape(re.sub(r"\s+", "", iban, flags=re.UNICODE)),
            re.IGNORECASE,
        )
        self.meta_code = meta_code

    def matches_header(self, line: str) -> bool:
        return self._expected_header_regex.match(line)

    def is_empty_line(self, line: str) -> bool:
        return line == '""'

    def get_account_number(self, line: Dict[str, str]) -> str:
        return line["Gläubiger-ID"]

    def get_amount(self, line: Dict[str, str]) -> str:
        return line["Betrag"].rstrip(" €")

    def get_booking_date(self, line: Dict[str, str]) -> date:
        return datetime.strptime(line["Buchungsdatum"], "%d.%m.%y").date()

    def get_booking_text(self, line: Dict[str, str]) -> str:
        return line["Umsatztyp"]

    def get_description(self, line: Dict[str, str]) -> str:
        return self.get_purpose(line)

    def get_payee(self, line: Dict[str, str]) -> str:
        type_ = line["Umsatztyp"]

        # if money is going out then payee should be the receiver
        # otherwise if money is coming in then payee should be the sender

        if type_ == "Ausgang":
            return line["Zahlungsempfänger*in"]
        elif type_ == "Eingang":
            return line["Zahlungspflichtige*r"]

        raise InvalidFormatError(f"Unknown Umsatztyp: {type_}")

    def get_purpose(self, line: Dict[str, str]) -> str:
        return line["Verwendungszweck"]
