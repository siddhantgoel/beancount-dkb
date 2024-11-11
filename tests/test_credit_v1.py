import datetime
from decimal import Decimal
from textwrap import dedent

import pytest
from beancount.core.data import Amount, Balance

from beancount_dkb import CreditImporter
from beancount_dkb.extractors.credit import V1Extractor

CARD_NUMBER = "1234********5678"

ENCODING = V1Extractor.file_encoding


def _format(string, kwargs):
    return dedent(string).format(**kwargs).lstrip()


@pytest.fixture
def tmp_file(tmp_path):
    return tmp_path / f"{CARD_NUMBER}.csv"


_extractor = V1Extractor(CARD_NUMBER)


@pytest.fixture(params=_extractor._get_possible_headers())
def header(request):
    yield request.param.value


def test_file_encoding_raises_deprecation_warning():
    with pytest.deprecated_call():
        CreditImporter(CARD_NUMBER, "Assets:DKB:Credit", file_encoding="utf-8")


def test_multiple_headers(tmp_file):
    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    common = """
        "Von:";"01.01.2018";
        "Bis:";"31.01.2018";
        "Saldo:";"5000.01 EUR";
        "Datum:";"30.01.2018";
    """

    # previous header format
    tmp_file.write_text(
        _format(
            """
            "Kreditkarte:";"{card_number} Kreditkarte";

            {common}

            """,
            dict(card_number=CARD_NUMBER, common=common),
        ),
        encoding=ENCODING,
    )

    assert importer.identify(tmp_file)

    # latest header format
    tmp_file.write_text(
        _format(
            """
            "Kreditkarte:";"{card_number}";

            {common}

            """,
            dict(card_number=CARD_NUMBER, common=common),
        ),
        encoding=ENCODING,
    )

    assert importer.identify(tmp_file)


def test_identify_correct(tmp_file, header):
    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    tmp_file.write_text(
        _format(
            """
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header}
            """,
            dict(card_number=CARD_NUMBER, header=header),
        ),
        encoding=ENCODING,
    )

    assert importer.identify(tmp_file)


def test_identify_prefixes(tmp_file, header):
    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    prefix = CARD_NUMBER[:4]
    suffix = CARD_NUMBER[-4:]

    tmp_file.write_text(
        _format(
            """
            "Kreditkarte:";"{prefix}********{suffix}";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header}
            """,
            dict(prefix=prefix, suffix=suffix, header=header),
        ),
        encoding=ENCODING,
    )

    assert importer.identify(tmp_file)


def test_identify_invalid_iban(tmp_file, header):
    other_iban = "5678********1234"

    tmp_file.write_text(
        _format(
            """
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header}
            """,
            dict(card_number=CARD_NUMBER, header=header),
        ),
        encoding=ENCODING,
    )

    importer = CreditImporter(other_iban, "Assets:DKB:Credit")

    assert not importer.identify(tmp_file)


def test_extract_no_transactions(tmp_file, header):
    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    tmp_file.write_text(
        _format(
            """
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header}
            """,
            dict(card_number=CARD_NUMBER, header=header),
        ),
        encoding=ENCODING,
    )

    directives = importer.extract(tmp_file)

    assert len(directives) == 1
    assert isinstance(directives[0], Balance)
    assert directives[0].date == datetime.date(2018, 1, 31)
    assert directives[0].amount == Amount(Decimal("5000.01"), currency="EUR")


def test_extract_transactions(tmp_file, header):
    tmp_file.write_text(
        _format(
            """
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header}
            "Ja";"15.01.2018";"15.01.2018";"REWE Filiale Muenchen";"-10,80";"";
            """,  # NOQA
            dict(card_number=CARD_NUMBER, header=header),
        ),
        encoding=ENCODING,
    )

    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    directives = importer.extract(tmp_file)

    assert len(directives) == 2
    assert directives[0].date == datetime.date(2018, 1, 15)

    assert len(directives[0].postings) == 1
    assert directives[0].postings[0].account == "Assets:DKB:Credit"
    assert directives[0].postings[0].units.currency == "EUR"
    assert directives[0].postings[0].units.number == Decimal("-10.80")


def test_extract_sets_timestamps(tmp_file, header):
    tmp_file.write_text(
        _format(
            """
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header}
            "Ja";"15.01.2018";"15.01.2018";"REWE Filiale Muenchen";"-10,80";"";
            """,  # NOQA
            dict(card_number=CARD_NUMBER, header=header),
        ),
        encoding=ENCODING,
    )

    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    assert not importer._date_from
    assert not importer._date_to
    assert not importer._balance_amount

    directives = importer.extract(tmp_file)

    assert directives
    assert importer._date_from == datetime.date(2018, 1, 1)
    assert importer._date_to == datetime.date(2018, 1, 31)
    assert importer._balance_date == datetime.date(2018, 1, 31)


def test_extract_with_zeitraum(tmp_file, header):
    tmp_file.write_text(
        _format(
            """
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Zeitraum:";"seit der letzten Abrechnung";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header}
            "Ja";"15.01.2018";"15.01.2018";"REWE Filiale Muenchen";"-10,80";"";
            """,  # NOQA
            dict(card_number=CARD_NUMBER, header=header),
        ),
        encoding=ENCODING,
    )

    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    assert not importer._date_from
    assert not importer._date_to
    assert not importer._balance_amount

    directives = importer.extract(tmp_file)

    assert directives
    assert not importer._date_from
    assert not importer._date_to
    assert importer._balance_date == datetime.date(2018, 1, 31)


def test_file_date_with_zeitraum(tmp_file, header):
    tmp_file.write_text(
        _format(
            """
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Zeitraum:";"seit der letzten Abrechnung";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header}
            "Ja";"15.01.2018";"15.01.2018";"REWE Filiale Muenchen";"-10,80";"";
            """,  # NOQA
            dict(card_number=CARD_NUMBER, header=header),
        ),
        encoding=ENCODING,
    )

    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    assert not importer._date_from
    assert not importer._date_to
    assert not importer._balance_amount

    assert importer.date(tmp_file) == datetime.date(2018, 1, 30)


def test_emits_closing_balance_directive(tmp_file, header):
    tmp_file.write_text(
        _format(
            """
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header}
            "Ja";"15.01.2018";"15.01.2018";"REWE Filiale Muenchen";"-10,80";"";
            """,  # NOQA
            dict(card_number=CARD_NUMBER, header=header),
        ),
        encoding=ENCODING,
    )

    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    directives = importer.extract(tmp_file)

    assert len(directives) == 2
    assert isinstance(directives[1], Balance)
    assert directives[1].date == datetime.date(2018, 1, 31)
    assert directives[1].amount == Amount(Decimal("5000.01"), currency="EUR")


def test_file_date_is_set_correctly(tmp_file, header):
    tmp_file.write_text(
        _format(
            """
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Von:";"01.01.2016";
            "Bis:";"31.01.2016";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header}
            "Ja";"15.01.2018";"15.01.2018";"REWE Filiale Muenchen";"-10,80";"";
            """,  # NOQA
            dict(card_number=CARD_NUMBER, header=header),
        ),
        encoding=ENCODING,
    )

    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    assert importer.date(tmp_file) == datetime.date(2016, 1, 31)


def test_extract_with_description_patterns(tmp_file, header):
    tmp_file.write_text(
        _format(
            """
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header}
            "Ja";"15.01.2018";"15.01.2018";"REWE Filiale Muenchen";"-10,80";"";
            """,  # NOQA
            dict(card_number=CARD_NUMBER, header=header),
        ),
        encoding=ENCODING,
    )

    importer = CreditImporter(
        CARD_NUMBER,
        "Assets:DKB:Credit",
        description_patterns=[("REWE Filiale", "Expenses:Supermarket:REWE")],
    )
    directives = importer.extract(tmp_file)

    assert len(directives) == 2
    assert len(directives[0].postings) == 2
    assert directives[0].postings[0].account == "Assets:DKB:Credit"
    assert directives[0].postings[0].units.currency == "EUR"
    assert directives[0].postings[0].units.number == Decimal("-10.80")

    assert directives[0].postings[1].account == "Expenses:Supermarket:REWE"
    assert directives[0].postings[1].units is None


def test_extract_multiple_transactions(tmp_file, header):
    # https://github.com/siddhantgoel/beancount-dkb/issues/123#issuecomment-1755167563
    prefix = CARD_NUMBER[:4]
    suffix = CARD_NUMBER[-4:]

    tmp_file.write_text(
        _format(
            """
            "Kreditkarte:";"{prefix}********{suffix}";

            "Zeitraum:";"letzten 60 Tage";
            "Saldo:";"1111.11 EUR";
            "Datum:";"29.09.2023";

            {header}
            "Ja";"23.09.2023";"22.09.2023";"HabenzinsenZ 000001111 T 030   0000";"1,11";"";
            "Ja";"23.08.2023";"22.08.2023";"HabenzinsenZ 000001111 T 031   0000";"1,11";"";
            """,  # NOQA
            dict(prefix=prefix, suffix=suffix, header=header),
        ),
        encoding=ENCODING,
    )

    importer = CreditImporter(CARD_NUMBER, "Assets:DKB:Credit")

    directives = importer.extract(tmp_file)

    assert len(directives) == 3
