import datetime
from decimal import Decimal
from textwrap import dedent

import pytest
from beancount.core.data import Amount, Balance

from beancount_dkb import ECImporter
from beancount_dkb.ec import V2Extractor

FORMATTED_IBAN = "DE99 9999 9999 9999 9999 99"

IBAN = FORMATTED_IBAN.replace(" ", "")

ENCODING = V2Extractor.file_encoding


def _format(string, kwargs):
    return dedent(string).format(**kwargs).lstrip()


_extractor = V2Extractor(IBAN)


@pytest.fixture(params=_extractor._get_possible_headers())
def header(request):
    yield request.param


@pytest.fixture
def tmp_file_no_transactions(tmp_path, header):
    """
    Fixture for a temporary file with no transactions
    """

    tmp_file = tmp_path / f"{IBAN}.csv"
    tmp_file.write_text(
        _format(
            """
            "Girokonto"{delimiter}"{iban}"
            ""
            "Kontostand vom 30.06.2023:"{delimiter}"5.000,01 EUR"
            ""
            {header}
            """,  # NOQA
            dict(iban=IBAN, header=header.value, delimiter=header.delimiter),
        ),
        encoding=ENCODING,
    )

    return tmp_file


@pytest.fixture
def tmp_file_single_transaction(tmp_path, header):
    """
    Fixture for a temporary file with a single transaction
    """

    tmp_file = tmp_path / f"{IBAN}.csv"
    tmp_file.write_text(
        _format(
            """
            "Girokonto"{delimiter}"{iban}"
            ""
            "Kontostand vom 30.06.2023:"{delimiter}"5.001,01 EUR"
            ""
            {header}
            "15.06.23"{delimiter}"15.06.23"{delimiter}"Gebucht"{delimiter}"ISSUER"{delimiter}"EDEKA//MUENCHEN/DE"{delimiter}"EDEKA SAGT DANKE"{delimiter}"Ausgang"{delimiter}"DE00000000000000000000"{delimiter}"-8,67"{delimiter}"DE9100112233445566"{delimiter}""{delimiter}"00000000000000000000000000"
            """,  # NOQA
            dict(iban=IBAN, header=header.value, delimiter=header.delimiter),
        ),
        encoding=ENCODING,
    )

    return tmp_file


@pytest.fixture
def tmp_file_multiple_transaction(tmp_path, header):
    """
    Fixture for a temporary file with multiple transactions
    """

    tmp_file = tmp_path / f"{IBAN}.csv"
    tmp_file.write_text(
        _format(
            """
            "Girokonto"{delimiter}"{iban}"
            ""
            "Kontostand vom 30.06.2023:"{delimiter}"5.000,01 EUR"
            ""
            {header}
            "01.06.23"{delimiter}"01.06.23"{delimiter}"Gebucht"{delimiter}"COMPANY INC"{delimiter}"MAX MUSTERMANN"{delimiter}"Lohn und Gehalt"{delimiter}"Eingang"{delimiter}"DE00000000000000000000"{delimiter}"1.000,0"{delimiter}""{delimiter}""{delimiter}""
            "15.06.23"{delimiter}"15.06.23"{delimiter}"Gebucht"{delimiter}"ISSUER"{delimiter}"EDEKA//MUENCHEN/DE"{delimiter}"EDEKA SAGT DANKE"{delimiter}"Ausgang"{delimiter}"DE00000000000000000000"{delimiter}"-8,67"{delimiter}"DE9100112233445566"{delimiter}""{delimiter}"00000000000000000000000000"
            "01.07.23"{delimiter}"01.07.23"{delimiter}"Gebucht"{delimiter}"MAX
            MUSTERMANN"{delimiter}"ERIKA MUSTERMANN"{delimiter}"MIETE"{delimiter}"Ausgang"{delimiter}"DE11111111111111111111"{delimiter}"-1.450"{delimiter}""{delimiter}""{delimiter}""
            """,  # NOQA
            dict(iban=IBAN, header=header.value, delimiter=header.delimiter),
        ),
        encoding=ENCODING,
    )

    return tmp_file


@pytest.fixture
def tmp_file_tagesgeld_no_transactions(tmp_path, header):
    """
    Fixture for a temporary file for a Savings account (i.e. "Tagesgeld")
    with no transactions
    """

    tmp_file = tmp_path / f"{IBAN}.csv"
    tmp_file.write_text(
        _format(
            """
            "Tagesgeld"{delimiter}"{iban}"
            ""
            "Kontostand vom 30.06.2023:"{delimiter}"5.000,01 EUR"
            ""
            {header}
            """,  # NOQA
            dict(iban=IBAN, header=header.value, delimiter=header.delimiter),
        ),
        encoding=ENCODING,
    )

    return tmp_file


def test_file_encoding_raises_deprecation_warning():
    with pytest.deprecated_call():
        ECImporter(IBAN, "Assets:DKB:EC", file_encoding="utf-8")


def test_identify_correct(tmp_file_single_transaction):
    importer = ECImporter(IBAN, "Assets:DKB:EC")

    assert importer.identify(tmp_file_single_transaction)


def test_identify_tagesgeld(tmp_file_tagesgeld_no_transactions):
    importer = ECImporter(IBAN, "Assets:DKB:Savings")

    assert importer.identify(tmp_file_tagesgeld_no_transactions)


def test_extract_no_transactions(tmp_file_no_transactions):
    importer = ECImporter(IBAN, "Assets:DKB:EC")

    directives = importer.extract(tmp_file_no_transactions)

    assert len(directives) == 1
    assert isinstance(directives[0], Balance)
    assert directives[0].date == datetime.date(2023, 7, 1)
    assert directives[0].amount == Amount(Decimal("5000.01"), currency="EUR")


def test_extract_no_transactions_euro_character(tmp_file_no_transactions):
    importer = ECImporter(IBAN, "Assets:DKB:EC")

    directives = importer.extract(tmp_file_no_transactions)

    assert len(directives) == 1
    assert isinstance(directives[0], Balance)
    assert directives[0].date == datetime.date(2023, 7, 1)
    assert directives[0].amount == Amount(Decimal("5000.01"), currency="EUR")


def test_extract_transactions(tmp_file_multiple_transaction):
    importer = ECImporter(IBAN, "Assets:DKB:EC")

    directives = importer.extract(tmp_file_multiple_transaction)

    assert len(directives) == 4

    assert directives[0].date == datetime.date(2023, 6, 1)
    assert directives[0].payee == "COMPANY INC"
    assert directives[0].narration == "Lohn und Gehalt"

    assert len(directives[1].postings) == 1
    assert directives[0].postings[0].account == "Assets:DKB:EC"
    assert directives[0].postings[0].units.currency == "EUR"
    assert directives[0].postings[0].units.number == Decimal("1000.00")

    assert directives[1].date == datetime.date(2023, 6, 15)
    assert directives[1].payee == "EDEKA//MUENCHEN/DE"
    assert directives[1].narration == "EDEKA SAGT DANKE"

    assert len(directives[1].postings) == 1
    assert directives[1].postings[0].account == "Assets:DKB:EC"
    assert directives[1].postings[0].units.currency == "EUR"
    assert directives[1].postings[0].units.number == Decimal("-8.67")

    assert directives[2].date == datetime.date(2023, 7, 1)
    assert directives[2].payee == "ERIKA MUSTERMANN"
    assert directives[2].narration == "MIETE"

    assert len(directives[2].postings) == 1
    assert directives[2].postings[0].account == "Assets:DKB:EC"
    assert directives[2].postings[0].units.currency == "EUR"
    assert directives[2].postings[0].units.number == Decimal("-1450")


def test_extract_sets_internal_values(tmp_file_single_transaction):
    importer = ECImporter(IBAN, "Assets:DKB:EC")

    assert not importer._date_from
    assert not importer._date_to
    assert not importer._balance_amount
    assert not importer._balance_date

    directives = importer.extract(tmp_file_single_transaction)

    assert directives
    assert importer._balance_amount == Amount(Decimal("5001.01"), currency="EUR")
    assert importer._balance_date == datetime.date(2023, 7, 1)


def test_emits_closing_balance_directive(tmp_file_single_transaction):
    importer = ECImporter(IBAN, "Assets:DKB:EC")

    directives = importer.extract(tmp_file_single_transaction)

    assert len(directives) == 2
    assert isinstance(directives[1], Balance)
    assert directives[1].date == datetime.date(2023, 7, 1)
    assert directives[1].amount == Amount(Decimal("5001.01"), currency="EUR")
    assert directives[1].meta["lineno"] == 3


def test_meta_code_is_added(tmp_file_single_transaction):
    importer = ECImporter(IBAN, "Assets:DKB:EC", meta_code="code")

    directives = importer.extract(tmp_file_single_transaction)

    assert len(directives) == 2
    assert directives[0].date == datetime.date(2023, 6, 15)
    assert directives[0].payee == "EDEKA//MUENCHEN/DE"
    assert directives[0].narration == "EDEKA SAGT DANKE"
    assert directives[0].meta["code"] == "Ausgang"


def test_extract_with_payee_patterns(tmp_file_single_transaction):
    importer = ECImporter(
        IBAN,
        "Assets:DKB:EC",
        payee_patterns=[("EDEKA", "Expenses:Supermarket:EDEKA")],
    )

    directives = importer.extract(tmp_file_single_transaction)

    assert len(directives) == 2
    assert len(directives[0].postings) == 2
    assert directives[0].postings[0].account == "Assets:DKB:EC"
    assert directives[0].postings[0].units.currency == "EUR"
    assert directives[0].postings[0].units.number == Decimal("-8.67")

    assert directives[0].postings[1].account == "Expenses:Supermarket:EDEKA"
    assert directives[0].postings[1].units is None


def test_extract_with_description_patterns(tmp_file_single_transaction):
    importer = ECImporter(
        IBAN,
        "Assets:DKB:EC",
        description_patterns=[("SAGT DANKE", "Expenses:Supermarket:EDEKA")],
    )

    directives = importer.extract(tmp_file_single_transaction)

    assert len(directives) == 2
    assert len(directives[0].postings) == 2
    assert directives[0].postings[0].account == "Assets:DKB:EC"
    assert directives[0].postings[0].units.currency == "EUR"
    assert directives[0].postings[0].units.number == Decimal("-8.67")

    assert directives[0].postings[1].account == "Expenses:Supermarket:EDEKA"
    assert directives[0].postings[1].units is None


def test_extract_with_payee_and_description_patterns(tmp_file_single_transaction):
    importer = ECImporter(
        IBAN,
        "Assets:DKB:EC",
        payee_patterns=[("EDEKA", "Expenses:Supermarket:EDEKA")],
        description_patterns=[("SAGT DANKE", "Expenses:Supermarket:EDEKA")],
    )

    with pytest.warns(UserWarning) as user_warnings:
        directives = importer.extract(tmp_file_single_transaction)

    assert len(directives) == 2
    assert len(directives[0].postings) == 2
    assert directives[0].postings[0].account == "Assets:DKB:EC"
    assert directives[0].postings[0].units.currency == "EUR"
    assert directives[0].postings[0].units.number == Decimal("-8.67")

    assert directives[0].postings[1].account == "Expenses:Supermarket:EDEKA"
    assert directives[0].postings[1].units is None

    assert len(user_warnings) == 1
    assert user_warnings[0].message.args[0] == (
        "Line 6 matches both payee_patterns and description_patterns. "
        "Picking payee_pattern."
    )
