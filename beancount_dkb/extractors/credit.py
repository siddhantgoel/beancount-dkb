import csv
from functools import partial
from collections import namedtuple
from datetime import date, datetime
from typing import Dict, Optional

from ..helpers import Header

Meta = namedtuple("Meta", ["value", "line_index"])


class BaseExtractor:
    def __init__(self, card_number: str):
        self.card_number = card_number

        self.filepath = None
        self._csv_delimiter = None

    def set_filepath(self, filepath: str):
        self.filepath = filepath

    @property
    def csv_reader(self):
        raise NotImplementedError()

    @property
    def csv_dict_reader(self):
        raise NotImplementedError()

    def get_account_number(self, line: Dict[str, str]) -> str:
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
        expected_header_prefixes = (
            f'"Kreditkarte:";"{self.card_number} Kreditkarte";',
            f'"Kreditkarte:";"{self.card_number}";',
            f'"Kreditkarte:";"{self.card_number[:4]}********{self.card_number[-4:]}";',
        )

        with open(self.filepath, encoding=self.file_encoding) as fd:
            line = fd.readline().strip()

            return any(line.startswith(header) for header in expected_header_prefixes)

    def _get_possible_headers(self) -> list[Header]:
        return [
            Header(";".join(f'"{field}"' for field in self.FIELDS) + ";", ";"),
        ]

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
        "Betrag (€)",
        "Fremdwährungsbetrag",
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
            header = self._get_applicable_header()

            if header is None:
                return False

            expected_prefix = (
                f'"Karte"{header.delimiter}"'
                f'Visa Kreditkarte"{header.delimiter}"'
                f"{self.card_number[:4]}"
            )

            with open(self.filepath, encoding=self.file_encoding) as fd:
                line = fd.readline().strip()

                return line.startswith(expected_prefix) and line.endswith(
                    f'{self.card_number[-4:]}"'
                )
        except UnicodeDecodeError:
            return False

    def _get_possible_headers(self) -> list[Header]:
        return [
            Header(",".join(f'"{field}"' for field in self.FIELDS), ","),
            Header(";".join(f'"{field}"' for field in self.FIELDS), ";"),
        ]

    def get_amount(self, line: Dict[str, str]) -> str:
        return line["Betrag (€)"].rstrip(" €")

    def get_valuation_date(self, line: Dict[str, str]) -> date:
        return datetime.strptime(line["Wertstellung"], "%d.%m.%y").date()

    def get_description(self, line: Dict[str, str]) -> str:
        return line["Beschreibung"]
