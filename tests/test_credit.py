import datetime
from decimal import Decimal
from textwrap import dedent

from beancount.core.data import Amount, Balance
import pytest

from beancount_dkb import CreditImporter
from beancount_dkb.credit import FIELDS

CARD_NUMBER = '1234********5678'

HEADER = ';'.join('"{}"'.format(field) for field in FIELDS)


def _format(string, kwargs):
    return dedent(string).format(**kwargs).lstrip().encode('utf-8')


@pytest.fixture
def tmp_file(tmpdir):
    return tmpdir.join('{}.csv'.format(CARD_NUMBER))


def test_multiple_headers(tmp_file):
    importer = CreditImporter(CARD_NUMBER, 'Assets:DKB:Credit')

    common = '''
        "Von:";"01.01.2018";
        "Bis:";"31.01.2018";
        "Saldo:";"5000.01 EUR";
        "Datum:";"30.01.2018";
    '''

    # previous header format
    tmp_file.write(
        _format(
            '''
            "Kreditkarte:";"{card_number} Kreditkarte";

            {common}

            ''',
            dict(card_number=CARD_NUMBER, common=common),
        )
    )

    with open(str(tmp_file.realpath())) as fd:
        assert importer.identify(fd)

    # latest header format
    tmp_file.write(
        _format(
            '''
            "Kreditkarte:";"{card_number}";

            {common}

            ''',
            dict(card_number=CARD_NUMBER, common=common),
        )
    )

    with open(str(tmp_file.realpath())) as fd:
        assert importer.identify(fd)


def test_identify_correct(tmp_file):
    importer = CreditImporter(CARD_NUMBER, 'Assets:DKB:Credit')

    tmp_file.write(
        _format(
            '''
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header};
            ''',
            dict(card_number=CARD_NUMBER, header=HEADER),
        )
    )

    with open(str(tmp_file.realpath())) as fd:
        assert importer.identify(fd)


def test_identify_invalid_iban(tmp_file):
    other_iban = '5678********1234'

    tmp_file.write(
        _format(
            '''
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header};
            ''',
            dict(card_number=CARD_NUMBER, header=HEADER),
        )
    )

    importer = CreditImporter(other_iban, 'Assets:DKB:Credit')

    with open(str(tmp_file.realpath())) as fd:
        assert not importer.identify(fd)


def test_extract_no_transactions(tmp_file):
    importer = CreditImporter(CARD_NUMBER, 'Assets:DKB:Credit')

    tmp_file.write(
        _format(
            '''
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header};
            ''',
            dict(card_number=CARD_NUMBER, header=HEADER),
        )
    )

    with open(str(tmp_file.realpath())) as fd:
        transactions = importer.extract(fd)

    assert len(transactions) == 1
    assert isinstance(transactions[0], Balance)
    assert transactions[0].date == datetime.date(2018, 1, 31)
    assert transactions[0].amount == Amount(Decimal('5000.01'), currency='EUR')


def test_extract_transactions(tmp_file):
    tmp_file.write(
        _format(
            '''
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header};
            "Ja";"15.01.2018";"15.01.2018";"REWE Filiale Muenchen";"-10,80";"";
            ''',  # NOQA
            dict(card_number=CARD_NUMBER, header=HEADER),
        )
    )

    importer = CreditImporter(
        CARD_NUMBER, 'Assets:DKB:Credit', file_encoding='utf-8'
    )

    with open(str(tmp_file.realpath())) as fd:
        transactions = importer.extract(fd)

    assert len(transactions) == 2
    assert transactions[0].date == datetime.date(2018, 1, 15)

    assert len(transactions[0].postings) == 1
    assert transactions[0].postings[0].account == 'Assets:DKB:Credit'
    assert transactions[0].postings[0].units.currency == 'EUR'
    assert transactions[0].postings[0].units.number == Decimal('-10.80')


def test_extract_sets_timestamps(tmp_file):
    tmp_file.write(
        _format(
            '''
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header};
            "Ja";"15.01.2018";"15.01.2018";"REWE Filiale Muenchen";"-10,80";"";
            ''',  # NOQA
            dict(card_number=CARD_NUMBER, header=HEADER),
        )
    )

    importer = CreditImporter(
        CARD_NUMBER, 'Assets:DKB:Credit', file_encoding='utf-8'
    )

    assert not importer._date_from
    assert not importer._date_to
    assert not importer._balance_amount

    with open(str(tmp_file.realpath())) as fd:
        transactions = importer.extract(fd)

    assert transactions
    assert importer._date_from == datetime.date(2018, 1, 1)
    assert importer._date_to == datetime.date(2018, 1, 31)
    assert importer._balance_date == datetime.date(2018, 1, 31)


def test_extract_with_zeitraum(tmp_file):
    tmp_file.write(
        _format(
            '''
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Zeitraum:";"seit der letzten Abrechnung";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header};
            "Ja";"15.01.2018";"15.01.2018";"REWE Filiale Muenchen";"-10,80";"";
            ''',  # NOQA
            dict(card_number=CARD_NUMBER, header=HEADER),
        )
    )

    importer = CreditImporter(
        CARD_NUMBER, 'Assets:DKB:Credit', file_encoding='utf-8'
    )

    assert not importer._date_from
    assert not importer._date_to
    assert not importer._balance_amount

    with open(str(tmp_file.realpath())) as fd:
        transactions = importer.extract(fd)

    assert transactions
    assert not importer._date_from
    assert not importer._date_to
    assert importer._balance_date == datetime.date(2018, 1, 31)


def test_file_date_with_zeitraum(tmp_file):
    tmp_file.write(
        _format(
            '''
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Zeitraum:";"seit der letzten Abrechnung";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header};
            "Ja";"15.01.2018";"15.01.2018";"REWE Filiale Muenchen";"-10,80";"";
            ''',  # NOQA
            dict(card_number=CARD_NUMBER, header=HEADER),
        )
    )

    importer = CreditImporter(
        CARD_NUMBER, 'Assets:DKB:Credit', file_encoding='utf-8'
    )

    assert not importer._date_from
    assert not importer._date_to
    assert not importer._balance_amount

    with open(str(tmp_file.realpath())) as fd:
        assert importer.file_date(fd) == datetime.date(2018, 1, 30)


def test_emits_closing_balance_directive(tmp_file):
    tmp_file.write(
        _format(
            '''
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Von:";"01.01.2018";
            "Bis:";"31.01.2018";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header};
            "Ja";"15.01.2018";"15.01.2018";"REWE Filiale Muenchen";"-10,80";"";
            ''',  # NOQA
            dict(card_number=CARD_NUMBER, header=HEADER),
        )
    )

    importer = CreditImporter(
        CARD_NUMBER, 'Assets:DKB:Credit', file_encoding='utf-8'
    )

    with open(str(tmp_file.realpath())) as fd:
        transactions = importer.extract(fd)

    assert len(transactions) == 2
    assert isinstance(transactions[1], Balance)
    assert transactions[1].date == datetime.date(2018, 1, 31)
    assert transactions[1].amount == Amount(Decimal('5000.01'), currency='EUR')


def test_file_date_is_set_correctly(tmp_file):
    tmp_file.write(
        _format(
            '''
            "Kreditkarte:";"{card_number} Kreditkarte";

            "Von:";"01.01.2016";
            "Bis:";"31.01.2016";
            "Saldo:";"5000.01 EUR";
            "Datum:";"30.01.2018";

            {header};
            "Ja";"15.01.2018";"15.01.2018";"REWE Filiale Muenchen";"-10,80";"";
            ''',  # NOQA
            dict(card_number=CARD_NUMBER, header=HEADER),
        )
    )

    importer = CreditImporter(
        CARD_NUMBER, 'Assets:DKB:Credit', file_encoding='utf-8'
    )

    with open(str(tmp_file.realpath())) as fd:
        assert importer.file_date(fd) == datetime.date(2016, 1, 31)
