import re
from collections import namedtuple
from datetime import date, datetime
from typing import Dict, Optional

from ..exceptions import InvalidFormatError

Meta = namedtuple("Meta", ["value", "line_index"])


class BaseExtractor:
    def __init__(self, iban: str, meta_code: Optional[str] = None):
        self.iban = iban
        self.meta_code = meta_code

    def identify(self, filepath: str) -> bool:
        raise NotImplementedError()

    def get_account_number(self, line: Dict[str, str]) -> str:
        raise NotImplementedError()

    def get_amount(self, line: Dict[str, str]) -> str:
        raise NotImplementedError()

    def get_booking_date(self, line: Dict[str, str]) -> date:
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

    HEADER = ";".join(f'"{field}"' for field in FIELDS) + ";"

    file_encoding = "ISO-8859-1"

    def identify(self, filepath: str) -> bool:
        regex = re.compile(
            r'^"Kontonummer:";"'
            + re.escape(re.sub(r"\s+", "", self.iban, flags=re.UNICODE))
            + r"\s",
            re.IGNORECASE,
        )

        with open(filepath, encoding=self.file_encoding) as fd:
            line = fd.readline().strip()

            return regex.match(line)

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
        "IBAN",
        "Betrag (€)",
        "Gläubiger-ID",
        "Mandatsreferenz",
        "Kundenreferenz",
    )

    HEADER = ";".join(f'"{field}"' for field in FIELDS)

    file_encoding = "utf-8-sig"

    def identify(self, filepath: str) -> bool:
        try:
            with open(filepath, encoding=self.file_encoding) as fd:
                lines = [line.strip() for line in fd.readlines()]

            return self.HEADER in lines
        except UnicodeDecodeError:
            return False

    def get_account_number(self, line: Dict[str, str]) -> str:
        return line["Gläubiger-ID"]

    def get_amount(self, line: Dict[str, str]) -> str:
        return line["Betrag (€)"].rstrip(" €")

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
