import datetime
from decimal import Decimal
from textwrap import dedent

from beancount.core.data import Amount, Balance
import pytest

from beancount_dkb import CreditImporter
from beancount_dkb.extractors.credit import V2Extractor

CARD_NUMBER = "1234 •••• •••• 5678"

HEADER = ";".join('"{}"'.format(field) for field in V2Extractor.FIELDS)


def _format(string, kwargs):
    return dedent(string).format(**kwargs).lstrip()


@pytest.fixture
def tmp_file(tmp_path):
    return tmp_path / f"{CARD_NUMBER}.csv"


def test_identify_correct(tmp_file):
    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    tmp_file.write_text(
        _format(
            """
            "Karte";"Visa-Kreditkarte {card_number}"
            ""
            "Saldo vom:";"5000.01 EUR"
            ""
            {header};
            """,
            dict(card_number=CARD_NUMBER, header=HEADER),
        )
    )

    with tmp_file.open() as fd:
        assert importer.identify(fd)


def test_identify_prefixes(tmp_file):
    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    prefix = CARD_NUMBER[:4]
    suffix = CARD_NUMBER[-4:]

    tmp_file.write_text(
        _format(
            """
            "Karte";"Visa-Kreditkarte {prefix} •••• •••• {suffix}"
            ""
            "Saldo:";"5000.01 EUR"
            ""
            {header};
            """,
            dict(prefix=prefix, suffix=suffix, header=HEADER),
        )
    )

    with tmp_file.open() as fd:
        assert importer.identify(fd)


def test_identify_invalid_iban(tmp_file):
    other_iban = "5678 •••• •••• 1234"

    tmp_file.write_text(
        _format(
            """
            "Karte";"Visa-Kreditkarte {card_number}"
            ""
            "Saldo:";"5000.01 EUR"
            ""
            {header};
            """,
            dict(card_number=CARD_NUMBER, header=HEADER),
        )
    )

    importer = CreditImporter(other_iban, "Assets:DKB:Credit")

    with tmp_file.open() as fd:
        assert not importer.identify(fd)


def test_extract_no_transactions(tmp_file):
    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    tmp_file.write_text(
        _format(
            """
            "Karte";"Visa-Kreditkarte {card_number}"
            ""
            "Saldo vom 31.01.2023:";"5000.01 EUR"
            ""
            {header};
            """,
            dict(card_number=CARD_NUMBER, header=HEADER),
        )
    )

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 1
    assert isinstance(directives[0], Balance)
    assert directives[0].date == datetime.date(2023, 1, 31)
    assert directives[0].amount == Amount(Decimal("5000.01"), currency="EUR")


def test_extract_transactions(tmp_file):
    tmp_file.write_text(
        _format(
            """
            "Karte";"Visa-Kreditkarte {card_number}"
            ""
            "Saldo:";"5000.01 EUR"
            ""
            {header};
            "15.01.23";"15.01.23";"Gebucht";"REWE Filiale Muenchen";"Im Geschäft";"-10,80 €";""
            """,  # NOQA
            dict(card_number=CARD_NUMBER, header=HEADER),
        )
    )

    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit", file_encoding="utf-8")

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 2
    assert directives[0].date == datetime.date(2023, 1, 15)

    assert len(directives[0].postings) == 1
    assert directives[0].postings[0].account == "Assets:DKB:Credit"
    assert directives[0].postings[0].units.currency == "EUR"
    assert directives[0].postings[0].units.number == Decimal("-10.80")


def test_emits_closing_balance_directive(tmp_file):
    tmp_file.write_text(
        _format(
            """
            "Karte";"Visa-Kreditkarte {card_number}"
            ""
            "Saldo vom 31.01.2023:";"5000.01 EUR"
            ""
            {header};
            "15.01.23";"15.01.23";"Gebucht";"REWE Filiale Muenchen";"Im Geschäft";"-10,80 €";""
            """,  # NOQA
            dict(card_number=CARD_NUMBER, header=HEADER),
        )
    )

    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit", file_encoding="utf-8")

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 2
    assert isinstance(directives[1], Balance)
    assert directives[1].date == datetime.date(2023, 1, 31)
    assert directives[1].amount == Amount(Decimal("5000.01"), currency="EUR")


def test_extract_with_description_patterns(tmp_file):
    tmp_file.write_text(
        _format(
            """
            "Karte";"Visa-Kreditkarte {card_number}";
            ""
            "Saldo:";"5000.01 EUR";
            ""
            {header};
            "15.01.23";"15.01.23";"Gebucht";"REWE Filiale Muenchen";"Im Geschäft";"-10,80 €";""
            """,  # NOQA
            dict(card_number=CARD_NUMBER, header=HEADER),
        )
    )

    importer = CreditImporter(
        CARD_NUMBER,
        "Assets:DKB:Credit",
        file_encoding="utf-8",
        description_patterns=[("REWE Filiale", "Expenses:Supermarket:REWE")],
    )
    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 2
    assert len(directives[0].postings) == 2
    assert directives[0].postings[0].account == "Assets:DKB:Credit"
    assert directives[0].postings[0].units.currency == "EUR"
    assert directives[0].postings[0].units.number == Decimal("-10.80")

    assert directives[0].postings[1].account == "Expenses:Supermarket:REWE"
    assert directives[0].postings[1].units is None