from collections import namedtuple
import csv
from functools import partial
import re
from datetime import date, datetime
from typing import Dict, Optional

from ..exceptions import InvalidFormatError
from ..helpers import Header

Meta = namedtuple("Meta", ["value", "line_index"])


class BaseExtractor:
    def __init__(self, iban: str, meta_code: Optional[str] = None):
        self.iban = iban
        self.meta_code = meta_code

        self.filepath = None
        self._csv_delimiter = None

    def set_filepath(self, filepath: str):
        self.filepath = filepath

    @property
    def csv_reader(self):
        raise NotImplementedError()

    def csv_dict_reader(self):
        raise NotImplementedError()

    def identify(self) -> bool:
        raise NotImplementedError()

    def extract_metadata_lines(self) -> list[str]:
        with open(self.filepath, encoding=self.file_encoding) as fd:
            lines = [line.strip() for line in fd.readlines()]

        for header in self._get_possible_headers():
            if header.value not in lines:
                continue

            header_index = lines.index(header.value)
            metadata_lines = lines[0:header_index]

            return metadata_lines

    def extract_transaction_lines(self) -> list[str]:
        with open(self.filepath, encoding=self.file_encoding) as fd:
            lines = [line.strip() for line in fd.readlines()]

        for header in self._get_possible_headers():
            if header.value not in lines:
                continue

            header_index = lines.index(header.value)
            transaction_lines = lines[header_index:]

            return transaction_lines

    def _get_possible_headers(self) -> list[Header]:
        """
        Return a list of possible header lines that the file could start with
        """

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

    file_encoding = "ISO-8859-1"

    @property
    def csv_reader(self):
        return partial(
            csv.reader, delimiter=";", quoting=csv.QUOTE_MINIMAL, quotechar='"'
        )

    @property
    def csv_dict_reader(self):
        return partial(
            csv.DictReader, delimiter=";", quoting=csv.QUOTE_MINIMAL, quotechar='"'
        )

    def identify(self) -> bool:
        regex = re.compile(
            r'^"Kontonummer:";"'
            + re.escape(re.sub(r"\s+", "", self.iban, flags=re.UNICODE))
            + r"\s",
            re.IGNORECASE,
        )

        with open(self.filepath, encoding=self.file_encoding) as fd:
            line = fd.readline().strip()

            return regex.match(line)

    def _get_possible_headers(self) -> list[Header]:
        return [
            Header(";".join(f'"{field}"' for field in self.FIELDS) + ";", ";"),
        ]

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

    file_encoding = "utf-8-sig"

    @property
    def csv_delimiter(self):
        if self._csv_delimiter is None:
            header = self._get_applicable_header()

            if header is not None:
                self._csv_delimiter = header.delimiter

        return self._csv_delimiter

    @property
    def csv_reader(self):
        assert self.csv_delimiter is not None

        return partial(
            csv.reader,
            delimiter=self.csv_delimiter,
            quoting=csv.QUOTE_MINIMAL,
            quotechar='"',
        )

    @property
    def csv_dict_reader(self):
        assert self.csv_delimiter is not None

        return partial(
            csv.DictReader,
            delimiter=self.csv_delimiter,
            quoting=csv.QUOTE_MINIMAL,
            quotechar='"',
        )

    def _get_possible_headers(self) -> list[Header]:
        return [
            Header(",".join(f'"{field}"' for field in self.FIELDS), ","),
            Header(";".join(f'"{field}"' for field in self.FIELDS), ";"),
        ]

    def _get_applicable_header(self) -> Optional[Header]:
        with open(self.filepath, encoding=self.file_encoding) as fd:
            lines = [line.strip() for line in fd.readlines()]

        return next(
            (
                header
                for header in self._get_possible_headers()
                if header.value in lines
            ),
            None,
        )

    def identify(self) -> bool:
        try:
            if self._get_applicable_header() is None:
                return False

            metadata_lines = self.extract_metadata_lines()

            regex = re.compile(
                r'^"(Girokonto|Tagesgeld)"'
                + self.csv_delimiter
                + '"'
                + re.escape(re.sub(r"\s+", "", self.iban, flags=re.UNICODE))
                + r'"',
                re.IGNORECASE,
            )

            for line in metadata_lines:
                if regex.match(line):
                    return True

            return False
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
