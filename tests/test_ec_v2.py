import datetime
from decimal import Decimal
from textwrap import dedent

from beancount.core.data import Amount, Balance
import pytest

from beancount_dkb import ECImporter
from beancount_dkb.ec import V2Extractor


FORMATTED_IBAN = "DE99 9999 9999 9999 9999 99"

IBAN = FORMATTED_IBAN.replace(" ", "")

HEADER = V2Extractor.HEADER

ENCODING = V2Extractor.file_encoding


def _format(string, kwargs):
    return dedent(string).format(**kwargs).lstrip()


@pytest.fixture
def tmp_file(tmp_path):
    return tmp_path / f"{IBAN}.csv"


def test_identify_correct(tmp_file):
    importer = ECImporter(IBAN, "Assets:DKB:EC")

    tmp_file.write_text(
        _format(
            """
            ""
            "Kontostand vom 30.06.2023:";"5.000,01 EUR";
            ""
            {header}
            "15.06.23";"15.06.23";"Gebucht";"ISSUER";"EDEKA//MUENCHEN/DE";"EDEKA SAGT DANKE";"Ausgang";"DE00000000000000000000";"-8,67";"DE9100112233445566";"";"00000000000000000000000000"
            """,  # NOQA
            dict(iban=IBAN, header=HEADER),
        ),
        encoding=ENCODING,
    )

    with tmp_file.open() as fd:
        assert importer.identify(fd)


def test_extract_no_transactions(tmp_file):
    importer = ECImporter(IBAN, "Assets:DKB:EC")

    tmp_file.write_text(
        _format(
            """
            ""
            "Kontostand vom 30.06.2023:";"5.000,01 EUR";
            ""
            {header}
            """,
            dict(iban=IBAN, header=HEADER),
        ),
        encoding=ENCODING,
    )

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 1
    assert isinstance(directives[0], Balance)
    assert directives[0].date == datetime.date(2023, 7, 1)
    assert directives[0].amount == Amount(Decimal("5000.01"), currency="EUR")


def test_extract_transactions(tmp_file):
    tmp_file.write_text(
        _format(
            """
            ""
            "Kontostand vom 30.06.2023:";"5001,01 EUR"
            ""
            {header}
            "01.06.23";"01.06.23";"Gebucht";"COMPANY INC";"MAX MUSTERMANN";"Lohn und Gehalt";"Eingang";"DE00000000000000000000";"1.000,0";"";"";""
            "15.06.23";"15.06.23";"Gebucht";"ISSUER";"EDEKA//MUENCHEN/DE";"EDEKA SAGT DANKE";"Ausgang";"DE00000000000000000000";"-8,67";"DE9100112233445566";"";"00000000000000000000000000"
            """,  # NOQA
            dict(iban=IBAN, header=HEADER),
        ),
        encoding=ENCODING,
    )

    importer = ECImporter(IBAN, "Assets:DKB:EC")

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 3

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

    assert len(directives[0].postings) == 1
    assert directives[1].postings[0].account == "Assets:DKB:EC"
    assert directives[1].postings[0].units.currency == "EUR"
    assert directives[1].postings[0].units.number == Decimal("-8.67")


def test_extract_sets_internal_values(tmp_file):
    tmp_file.write_text(
        _format(
            """
            ""
            "Kontostand vom 30.06.2023:";"5001,01 EUR"
            ""
            {header}
            "15.06.23";"15.06.23";"Gebucht";"ISSUER";"EDEKA//MUENCHEN/DE";"EDEKA SAGT DANKE";"Ausgang";"DE00000000000000000000";"-8,67";"DE9100112233445566";"";"00000000000000000000000000"
            """,  # NOQA
            dict(iban=IBAN, header=HEADER),
        ),
        encoding=ENCODING,
    )

    importer = ECImporter(IBAN, "Assets:DKB:EC")

    assert not importer._date_from
    assert not importer._date_to
    assert not importer._balance_amount
    assert not importer._balance_date

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert directives
    assert importer._balance_amount == Amount(Decimal("5001.01"), currency="EUR")
    assert importer._balance_date == datetime.date(2023, 7, 1)


def test_emits_closing_balance_directive(tmp_file):
    tmp_file.write_text(
        _format(
            """
            ""
            "Kontostand vom 30.06.2023:";"5001,01 EUR"
            ""
            {header}
            "15.06.23";"15.06.23";"Gebucht";"ISSUER";"EDEKA//MUENCHEN/DE";"EDEKA SAGT DANKE";"Ausgang";"DE00000000000000000000";"-8,67";"DE9100112233445566";"";"00000000000000000000000000"
            """,  # NOQA
            dict(iban=IBAN, header=HEADER),
        ),
        encoding=ENCODING,
    )

    importer = ECImporter(IBAN, "Assets:DKB:EC")

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 2
    assert isinstance(directives[1], Balance)
    assert directives[1].date == datetime.date(2023, 7, 1)
    assert directives[1].amount == Amount(Decimal("5001.01"), currency="EUR")
    assert directives[1].meta["lineno"] == 2


def test_meta_code_is_added(tmp_file):
    tmp_file.write_text(
        _format(
            """
            ""
            "Kontostand vom 30.06.2023:";"5001,01 EUR"
            ""
            {header}
            "15.06.23";"15.06.23";"Gebucht";"ISSUER";"EDEKA//MUENCHEN/DE";"EDEKA SAGT DANKE";"Ausgang";"DE00000000000000000000";"-8,67";"DE9100112233445566";"";"00000000000000000000000000"
            """,  # NOQA
            dict(iban=IBAN, header=HEADER),
        ),
        encoding=ENCODING,
    )

    importer = ECImporter(IBAN, "Assets:DKB:EC", meta_code="code")

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 2
    assert directives[0].date == datetime.date(2023, 6, 15)
    assert directives[0].payee == "EDEKA//MUENCHEN/DE"
    assert directives[0].narration == "EDEKA SAGT DANKE"
    assert directives[0].meta["code"] == "Ausgang"


def test_extract_with_payee_patterns(tmp_file):
    tmp_file.write_text(
        _format(
            """
            ""
            "Kontostand vom 30.06.2023:";"5001,01 EUR"
            ""
            {header}
            "15.06.23";"15.06.23";"Gebucht";"ISSUER";"EDEKA//MUENCHEN/DE";"EDEKA SAGT DANKE";"Ausgang";"DE00000000000000000000";"-8,67";"DE9100112233445566";"";"00000000000000000000000000"
            """,  # NOQA
            dict(iban=IBAN, header=HEADER),
        ),
        encoding=ENCODING,
    )

    importer = ECImporter(
        IBAN,
        "Assets:DKB:EC",
        payee_patterns=[("EDEKA", "Expenses:Supermarket:EDEKA")],
    )

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 2
    assert len(directives[0].postings) == 2
    assert directives[0].postings[0].account == "Assets:DKB:EC"
    assert directives[0].postings[0].units.currency == "EUR"
    assert directives[0].postings[0].units.number == Decimal("-8.67")

    assert directives[0].postings[1].account == "Expenses:Supermarket:EDEKA"
    assert directives[0].postings[1].units is None


def test_extract_with_description_patterns(tmp_file):
    tmp_file.write_text(
        _format(
            """
            ""
            "Kontostand vom 30.06.2023:";"5001,01 EUR"
            ""
            {header}
            "15.06.23";"15.06.23";"Gebucht";"ISSUER";"EDEKA//MUENCHEN/DE";"EDEKA SAGT DANKE";"Ausgang";"DE00000000000000000000";"-8,67";"DE9100112233445566";"";"00000000000000000000000000"
            """,  # NOQA
            dict(iban=IBAN, header=HEADER),
        ),
        encoding=ENCODING,
    )

    importer = ECImporter(
        IBAN,
        "Assets:DKB:EC",
        description_patterns=[("SAGT DANKE", "Expenses:Supermarket:EDEKA")],
    )

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 2
    assert len(directives[0].postings) == 2
    assert directives[0].postings[0].account == "Assets:DKB:EC"
    assert directives[0].postings[0].units.currency == "EUR"
    assert directives[0].postings[0].units.number == Decimal("-8.67")

    assert directives[0].postings[1].account == "Expenses:Supermarket:EDEKA"
    assert directives[0].postings[1].units is None


def test_extract_with_payee_and_description_patterns(tmp_file):
    tmp_file.write_text(
        _format(
            """
            ""
            "Kontostand vom 30.06.2023:";"5001,01 EUR"
            ""
            {header}
            "15.06.23";"15.06.23";"Gebucht";"ISSUER";"EDEKA//MUENCHEN/DE";"EDEKA SAGT DANKE";"Ausgang";"DE00000000000000000000";"-8,67";"DE9100112233445566";"";"00000000000000000000000000"
            """,  # NOQA
            dict(iban=IBAN, header=HEADER),
        ),
        encoding=ENCODING,
    )

    importer = ECImporter(
        IBAN,
        "Assets:DKB:EC",
        payee_patterns=[("EDEKA", "Expenses:Supermarket:EDEKA")],
        description_patterns=[("SAGT DANKE", "Expenses:Supermarket:EDEKA")],
    )

    with tmp_file.open() as fd:
        with pytest.warns(UserWarning) as user_warnings:
            directives = importer.extract(fd)

    assert len(directives) == 2
    assert len(directives[0].postings) == 2
    assert directives[0].postings[0].account == "Assets:DKB:EC"
    assert directives[0].postings[0].units.currency == "EUR"
    assert directives[0].postings[0].units.number == Decimal("-8.67")

    assert directives[0].postings[1].account == "Expenses:Supermarket:EDEKA"
    assert directives[0].postings[1].units is None

    assert len(user_warnings) == 1
    assert user_warnings[0].message.args[0] == (
        "Line 5 matches both payee_patterns and description_patterns. "
        "Picking payee_pattern."
    )
