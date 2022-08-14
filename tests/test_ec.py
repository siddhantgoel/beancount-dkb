import datetime
from decimal import Decimal
from textwrap import dedent

from beancount.core.data import Amount, Balance
import pytest

from beancount_dkb import ECImporter
from beancount_dkb.ec import FIELDS


FORMATTED_IBAN = 'DE99 9999 9999 9999 9999 99'

IBAN = FORMATTED_IBAN.replace(' ', '')

HEADER = ';'.join('"{}"'.format(field) for field in FIELDS)


def _format(string, kwargs):
    return dedent(string).format(**kwargs).lstrip()


@pytest.fixture
def tmp_file(tmp_path):
    return tmp_path / f'{IBAN}.csv'


def test_identify_correct(tmp_file):
    importer = ECImporter(IBAN, 'Assets:DKB:EC')

    tmp_file.write_text(
        _format(
            '''
            "Kontonummer:";"{iban} / Girokonto";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Kontostand vom 31.01.2018:";"5.000,01 EUR";

            {header};
            ''',
            dict(iban=IBAN, header=HEADER),
        )
    )

    with tmp_file.open() as fd:
        assert importer.identify(fd)


def test_identify_with_nonstandard_account_name(tmp_file):
    importer = ECImporter(IBAN, 'Assets:DKB:EC')

    tmp_file.write_text(
        _format(
            '''
            "Kontonummer:";"{iban} / My Custom Named Account";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Kontostand vom 31.01.2018:";"5.000,01 EUR";

            {header};
            ''',
            dict(iban=IBAN, header=HEADER),
        )
    )

    with tmp_file.open() as fd:
        assert importer.identify(fd)


def test_identify_with_exotic_account_name(tmp_file):
    importer = ECImporter(IBAN, 'Assets:DKB:EC')

    tmp_file.write_text(
        _format(
            '''
            "Kontonummer:";"{iban} / Girökóntô, Γιροκοντώ, 預金, حساب البنك";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Kontostand vom 31.01.2018:";"5.000,01 EUR";

            {header};
            ''',  # NOQA
            dict(iban=IBAN, header=HEADER),
        )
    )

    with tmp_file.open() as fd:
        assert importer.identify(fd)


def test_identify_with_formatted_iban(tmp_file):
    importer = ECImporter(FORMATTED_IBAN, 'Assets:DKB:EC')

    tmp_file.write_text(
        _format(
            '''
            "Kontonummer:";"{iban} / Girokonto";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Kontostand vom 31.01.2018:";"5.000,01 EUR";

            {header};
            ''',
            dict(iban=IBAN, header=HEADER),
        )
    )

    with tmp_file.open() as fd:
        assert importer.identify(fd)


def test_identify_invalid_iban(tmp_file):
    other_iban = 'DE00000000000000000000'

    tmp_file.write_text(
        _format(
            '''
            "Kontonummer:";"{iban} / Girokonto";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Kontostand vom 31.01.2018:";"5.000,01 EUR";

            {header};
            ''',
            dict(iban=IBAN, header=HEADER),
        )
    )

    importer = ECImporter(other_iban, 'Assets:DKB:EC')

    with tmp_file.open() as fd:
        assert not importer.identify(fd)


def test_extract_no_transactions(tmp_file):
    importer = ECImporter(IBAN, 'Assets:DKB:EC')

    tmp_file.write_text(
        _format(
            '''
            "Kontonummer:";"{iban} / Girokonto";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Kontostand vom 31.01.2018:";"5.000,01 EUR";

            {header};
            ''',
            dict(iban=IBAN, header=HEADER),
        )
    )

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 1
    assert isinstance(directives[0], Balance)
    assert directives[0].date == datetime.date(2018, 2, 1)
    assert directives[0].amount == Amount(Decimal('5000.01'), currency='EUR')


def test_extract_transactions(tmp_file):
    tmp_file.write_text(
        _format(
            '''
            "Kontonummer:";"{iban} / Girokonto";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Kontostand vom 31.01.2018:";"5.000,01 EUR";

            {header};
            "16.01.2018";"16.01.2018";"Lastschrift";"REWE Filialen Voll";"REWE SAGT DANKE.";"DE00000000000000000000";"AAAAAAAA";"-15,37";"000000000000000000    ";"0000000000000000000000";"";
            "06.05.2020";"06.05.2020";"Gutschrift";"From Someone";"";"DE88700222000012345678";"FDDODEMMXXX";"1,00";"";"";"NOTPROVIDED";
            ''',  # NOQA
            dict(iban=IBAN, header=HEADER),
        )
    )

    importer = ECImporter(IBAN, 'Assets:DKB:EC', file_encoding='utf-8')

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 3
    assert directives[0].date == datetime.date(2018, 1, 16)
    assert directives[0].payee == 'REWE Filialen Voll'
    assert directives[0].narration == 'Lastschrift REWE SAGT DANKE.'

    assert len(directives[0].postings) == 1
    assert directives[0].postings[0].account == 'Assets:DKB:EC'
    assert directives[0].postings[0].units.currency == 'EUR'
    assert directives[0].postings[0].units.number == Decimal('-15.37')

    assert directives[1].date == datetime.date(2020, 5, 6)
    assert directives[1].payee == 'From Someone'
    assert directives[1].narration == 'Gutschrift DE88700222000012345678'

    assert len(directives[1].postings) == 1
    assert directives[1].postings[0].account == 'Assets:DKB:EC'
    assert directives[1].postings[0].units.currency == 'EUR'
    assert directives[1].postings[0].units.number == Decimal('1.00')


def test_extract_sets_timestamps(tmp_file):
    tmp_file.write_text(
        _format(
            '''
            "Kontonummer:";"{iban} / Girokonto";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Kontostand vom 31.01.2018:";"5.000,01 EUR";

            {header};
            "16.01.2018";"16.01.2018";"Lastschrift";"REWE Filialen Voll";"REWE SAGT DANKE.";"DE00000000000000000000";"AAAAAAAA";"-15,37";"000000000000000000    ";"0000000000000000000000";"";
            ''',  # NOQA
            dict(iban=IBAN, header=HEADER),
        )
    )

    importer = ECImporter(IBAN, 'Assets:DKB:EC', file_encoding='utf-8')

    assert not importer._date_from
    assert not importer._date_to
    assert not importer._balance_amount
    assert not importer._balance_date

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert directives
    assert importer._date_from == datetime.date(2018, 1, 1)
    assert importer._date_to == datetime.date(2018, 1, 31)
    assert importer._balance_amount == Amount(
        Decimal('5000.01'), currency='EUR'
    )
    assert importer._balance_date == datetime.date(2018, 2, 1)


def test_tagessaldo_emits_balance_directive(tmp_file):
    tmp_file.write_text(
        _format(
            '''
            "Kontonummer:";"{iban} / Girokonto";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Kontostand vom 31.01.2018:";"5.000,01 EUR";

            {header};
            "20.01.2018";"";"";"";"Tagessaldo";"";"";"2.500,01";
            ''',
            dict(iban=IBAN, header=HEADER),
        )
    )

    importer = ECImporter(IBAN, 'Assets:DKB:EC', file_encoding='utf-8')

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 2
    assert isinstance(directives[0], Balance)
    assert directives[0].date == datetime.date(2018, 1, 21)
    assert directives[0].amount == Amount(Decimal('2500.01'), currency='EUR')


def test_tagessaldo_with_empty_balance_does_not_crash(tmp_file):
    tmp_file.write_text(
        _format(
            '''
            "Kontonummer:";"{iban} / Girokonto";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Kontostand vom 31.01.2018:";"5.000,01 EUR";

            {header};
            "20.01.2018";"";"";"";"Tagessaldo";"";"";"";
            ''',
            dict(iban=IBAN, header=HEADER),
        )
    )

    importer = ECImporter(IBAN, 'Assets:DKB:EC', file_encoding='utf-8')

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 1
    assert isinstance(directives[0], Balance)
    assert directives[0].date == datetime.date(2018, 2, 1)
    assert directives[0].amount == Amount(Decimal('5000.01'), currency='EUR')


def test_file_date_is_set_correctly(tmp_file):
    tmp_file.write_text(
        _format(
            '''
            "Kontonummer:";"{iban} / Girokonto";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Kontostand vom 31.01.2018:";"5.000,01 EUR";

            {header};
            "20.01.2018";"";"";"";"Tagessaldo";"";"";"2.500,01";
            ''',
            dict(iban=IBAN, header=HEADER),
        )
    )

    importer = ECImporter(IBAN, 'Assets:DKB:EC', file_encoding='utf-8')

    with tmp_file.open() as fd:
        assert importer.file_date(fd) == datetime.date(2018, 1, 31)


def test_emits_closing_balance_directive(tmp_file):
    tmp_file.write_text(
        _format(
            '''
            "Kontonummer:";"{iban} / Girokonto";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Kontostand vom 31.01.2018:";"5.000,01 EUR";

            {header};
            "16.01.2018";"16.01.2018";"Lastschrift";"REWE Filialen Voll";"REWE SAGT DANKE.";"DE00000000000000000000";"AAAAAAAA";"-15,37";"000000000000000000    ";"0000000000000000000000";"";
            ''',  # NOQA
            dict(iban=IBAN, header=HEADER),
        )
    )

    importer = ECImporter(IBAN, 'Assets:DKB:EC', file_encoding='utf-8')

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 2
    assert isinstance(directives[1], Balance)
    assert directives[1].date == datetime.date(2018, 2, 1)
    assert directives[1].amount == Amount(Decimal('5000.01'), currency='EUR')


def test_mismatching_dates_in_meta(tmp_file):
    tmp_file.write_text(
        _format(
            '''
            "Kontonummer:";"{iban} / Girokonto";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Kontostand vom 31.01.2019:";"5.000,01 EUR";

            {header};
            "16.01.2018";"16.01.2018";"Lastschrift";"REWE Filialen Voll";"REWE SAGT DANKE.";"DE00000000000000000000";"AAAAAAAA";"-15,37";"000000000000000000    ";"0000000000000000000000";"";
            ''',  # NOQA
            dict(iban=IBAN, header=HEADER),
        )
    )

    importer = ECImporter(IBAN, 'Assets:DKB:EC', file_encoding='utf-8')

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 2
    assert isinstance(directives[1], Balance)
    assert directives[1].date == datetime.date(2019, 2, 1)
    assert directives[1].amount == Amount(Decimal('5000.01'), currency='EUR')


def test_meta_code_is_added(tmp_file):
    tmp_file.write_text(
        _format(
            '''
            "Kontonummer:";"{iban} / Girokonto";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Kontostand vom 31.01.2018:";"5.000,01 EUR";

            {header};
            "16.01.2018";"16.01.2018";"Lastschrift";"REWE Filialen Voll";"REWE SAGT DANKE.";"DE00000000000000000000";"AAAAAAAA";"-15,37";"000000000000000000    ";"0000000000000000000000";"";
            ''',  # NOQA
            dict(iban=IBAN, header=HEADER),
        )
    )

    importer = ECImporter(
        IBAN, 'Assets:DKB:EC', file_encoding='utf-8', meta_code='code'
    )

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 2
    assert directives[0].date == datetime.date(2018, 1, 16)
    assert directives[0].payee == 'REWE Filialen Voll'
    assert directives[0].narration == 'REWE SAGT DANKE.'
    assert directives[0].meta['code'] == 'Lastschrift'


def test_extract_with_payee_patterns(tmp_file):
    tmp_file.write_text(
        _format(
            '''
            "Kontonummer:";"{iban} / Girokonto";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Kontostand vom 31.01.2018:";"5.000,01 EUR";

            {header};
            "16.01.2018";"16.01.2018";"Lastschrift";"REWE Filialen Voll";"REWE SAGT DANKE.";"DE00000000000000000000";"AAAAAAAA";"-15,37";"000000000000000000    ";"0000000000000000000000";"";
            ''',  # NOQA
            dict(iban=IBAN, header=HEADER),
        )
    )

    importer = ECImporter(
        IBAN,
        'Assets:DKB:EC',
        file_encoding='utf-8',
        payee_patterns=[('REWE Filialen', 'Expenses:Supermarket:REWE')]
    )

    with tmp_file.open() as fd:
        directives = importer.extract(fd)

    assert len(directives) == 2
    assert len(directives[0].postings) == 2
    assert directives[0].postings[0].account == 'Assets:DKB:EC'
    assert directives[0].postings[0].units.currency == 'EUR'
    assert directives[0].postings[0].units.number == Decimal('-15.37')

    assert directives[0].postings[1].account == 'Expenses:Supermarket:REWE'
    assert directives[0].postings[1].units == None
