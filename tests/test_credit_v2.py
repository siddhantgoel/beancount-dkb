import datetime
from decimal import Decimal
from textwrap import dedent

import pytest
from beancount.core.data import Amount, Balance

from beancount_dkb import CreditImporter
from beancount_dkb.extractors.credit import V2Extractor

CARD_NUMBER = "1234 •••• •••• 5678"


def _format(string, kwargs):
    return dedent(string).format(**kwargs).lstrip()


@pytest.fixture
def tmp_file(tmp_path):
    return tmp_path / f"{CARD_NUMBER}.csv"


_extractor = V2Extractor(CARD_NUMBER)


@pytest.fixture(params=_extractor._get_possible_headers())
def header(request):
    yield request.param


@pytest.fixture
def tmp_file_no_transactions(tmp_path, header):
    """
    Fixture for a temporary file with no transactions
    """

    tmp_file = tmp_path / f"{CARD_NUMBER}.csv"
    tmp_file.write_text(
        _format(
            """
            "Karte"{delimiter}"Visa Kreditkarte"{delimiter}"{card_number}"
            ""
            "Saldo vom 31.01.2023:"{delimiter}"5000.01 EUR"
            ""
            {header}
            """,
            dict(
                card_number=CARD_NUMBER, header=header.value, delimiter=header.delimiter
            ),
        )
    )

    return tmp_file


@pytest.fixture
def tmp_file_single_transaction(tmp_path, header):
    """
    Fixture for a temporary file with a single transaction
    """

    tmp_file = tmp_path / f"{CARD_NUMBER}.csv"
    tmp_file.write_text(
        _format(
            """
            "Karte"{delimiter}"Visa Kreditkarte"{delimiter}"{card_number}"
            ""
            "Saldo vom 31.01.2023:"{delimiter}"5000.01 EUR"
            ""
            {header}
            "15.01.23"{delimiter}"15.01.23"{delimiter}"Gebucht"{delimiter}"REWE Filiale Muenchen"{delimiter}"Im Geschäft"{delimiter}"-10,80 €"{delimiter}""
            """,
            dict(
                card_number=CARD_NUMBER, header=header.value, delimiter=header.delimiter
            ),
        )
    )

    return tmp_file


def test_identify_correct(tmp_file_single_transaction):
    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    assert importer.identify(tmp_file_single_transaction)


def test_identify_invalid_iban(tmp_file_no_transactions):
    other_iban = "5678 •••• •••• 1234"

    importer = CreditImporter(other_iban, "Assets:DKB:Credit")

    assert not importer.identify(tmp_file_no_transactions)


def test_extract_no_transactions(tmp_file_no_transactions):
    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    directives = importer.extract(tmp_file_no_transactions)

    assert len(directives) == 1
    assert isinstance(directives[0], Balance)
    assert directives[0].date == datetime.date(2023, 1, 31)
    assert directives[0].amount == Amount(Decimal("5000.01"), currency="EUR")


def test_extract_transactions(tmp_file_single_transaction):
    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    directives = importer.extract(tmp_file_single_transaction)

    assert len(directives) == 2
    assert directives[0].date == datetime.date(2023, 1, 15)

    assert len(directives[0].postings) == 1
    assert directives[0].postings[0].account == "Assets:DKB:Credit"
    assert directives[0].postings[0].units.currency == "EUR"
    assert directives[0].postings[0].units.number == Decimal("-10.80")


def test_emits_closing_balance_directive(tmp_file_single_transaction):
    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    directives = importer.extract(tmp_file_single_transaction)

    assert len(directives) == 2
    assert isinstance(directives[1], Balance)
    assert directives[1].date == datetime.date(2023, 1, 31)
    assert directives[1].amount == Amount(Decimal("5000.01"), currency="EUR")


def test_extract_with_description_patterns(tmp_file_single_transaction):
    importer = CreditImporter(
        CARD_NUMBER,
        "Assets:DKB:Credit",
        description_patterns=[("REWE Filiale", "Expenses:Supermarket:REWE")],
    )
    directives = importer.extract(tmp_file_single_transaction)

    assert len(directives) == 2
    assert len(directives[0].postings) == 2
    assert directives[0].postings[0].account == "Assets:DKB:Credit"
    assert directives[0].postings[0].units.currency == "EUR"
    assert directives[0].postings[0].units.number == Decimal("-10.80")

    assert directives[0].postings[1].account == "Expenses:Supermarket:REWE"
    assert directives[0].postings[1].units is None


def test_comma_separator_in_balance(tmp_file_single_transaction):
    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    directives = importer.extract(tmp_file_single_transaction)

    assert len(directives) == 2
    assert isinstance(directives[1], Balance)
    assert directives[1].amount == Amount(Decimal("5000.01"), currency="EUR")
