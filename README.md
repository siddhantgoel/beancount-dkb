# Beancount DKB Importer

[![image](https://img.shields.io/pypi/v/beancount-dkb.svg)](https://pypi.python.org/pypi/beancount-dkb)
[![image](https://img.shields.io/pypi/pyversions/beancount-dkb.svg)](https://pypi.python.org/pypi/beancount-dkb)
[![Downloads](https://static.pepy.tech/badge/beancount-dkb)](https://pepy.tech/project/beancount-dkb)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

`beancount-dkb` provides importers for converting CSV exports of [DKB] (Deutsche
Kreditbank) account summaries to the [Beancount] format.

## Installation

```sh
$ pip install beancount-dkb
```

In case you prefer installing from the Github repository, please note that `main` is the
development branch so `stable` is what you should be installing from.

Note that v1.x will *only* work with Beancount 3.x, while v0.x will *only* work with
Beancount 2.x, due to incompatibilities between Beancount 3.x and 2.x.

## Usage

If you're not familiar with how to import external data into Beancount, please read
[this guide] first.

### Beancount 3.x

Beancount 3.x has replaced the `config.py` file based workflow in favor of having a
script based workflow, as per the [changes documented here]. As a result, the importer's
initialization parameters have been shifted to `pyproject.toml`.

Add the following to your `pyproject.toml` in your project root.

```toml
[tool.beancount-dkb.ec]
iban = "DE99 9999 9999 9999 9999 99"
account_name = "Assets:DKB:EC"
currency = "EUR"

[tool.beancount-dkb.credit]
card_number = "9999 9999 9999 9999"
account_name = "Assets:DKB:Credit"
currency = "EUR"
```

Run `beancount-dkb-ec` or `beancount-dkb-credit` to call the importer. The `identify`
and `extract` subcommands would identify the file and extract transactions for you.

```sh
$ beancount-dkb-ec extract transaction.csv >> you.beancount
$ beancount-dkb-credit extract transaction.csv >> you.beancount
```

### Beancount 2.x

Adjust your [config file] to include `ECImporter` and `CreditImporter`
(depending on what account you're trying to import).

Add the following to your `config.py`.

```python
from beancount_dkb import ECImporter, CreditImporter

IBAN_NUMBER = 'DE99 9999 9999 9999 9999 99' # your real IBAN number

CARD_NUMBER = '9999 9999 9999 9999'         # your real Credit Card number

CONFIG = [
    ECImporter(
        IBAN_NUMBER,
        'Assets:DKB:EC',
        currency='EUR',
    ),

    CreditImporter(
        CARD_NUMBER,
        'Assets:DKB:Credit',
        currency='EUR',
    )
]
```

Once this is in place, you should be able to run `bean-extract` on the command
line to extract the transactions and pipe all of them into your Beancount file.

```sh
$ bean-extract /path/to/config.py transaction.csv >> you.beancount
```

### Transaction Codes as Meta Tags

By default, the ECImporter prepends the transaction code ("Buchungstext") to the
transaction description. To achieve shorter descriptions and use meta tags to query for
certain transaction codes, the importer may be configured to store the transaction code
in a user provided meta tag.

Add the `meta_code` parameter to the `ECImporter` initializer.

#### Beancount 3.x

```toml
[tool.beancount-dkb.ec]
iban = "DE99 9999 9999 9999 9999 99"
account_name = "Assets:DKB:EC"
meta_code = "code"
```

#### Beancount 2.x

```python
...
CONFIG = [
    ECImporter(
        IBAN_NUMBER,
        'Assets:DKB:EC',
        currency='EUR',
        meta_code='code',
    ),
...

```

This is how an example transaction looks without the option:

```beancount
2021-03-01 * "Kartenzahlung" "XY Supermarket"
    Assets:DKB:EC                        -133.72 EUR
```

And this is the resulting transaction using `meta_code='code'`

```beancount
2021-03-01 * "XY Supermarket"
    code: Kartenzahlung
    Assets:DKB:EC                        -133.72 EUR
```

### Pattern-matching Transactions

It's possible to give the importer classes hints if you'd like them to include a
second posting based on specific characteristics of the original transaction.

For instance, if the payee or the description in a transaction always matches a
certain value, it's possible to tell the `ECImporter` or `CreditImporter` to
automatically place a second posting in the returned lits of transactions.

#### `ECImporter`

`ECImporter` accepts `payee_patterns` and `description_patterns` arguments, which should
be a list of `(pattern, account)` tuples.

##### Beancount 3.x

```toml
[tool.beancount-dkb.ec]
iban = "DE99 9999 9999 9999 9999 99"
account_name = "Assets:DKB:EC"
payee_patterns = [
    ["REWE", "Expenses:Supermarket:REWE"],
    ["NETFLIX", "Expenses:Online:Netflix"],
]
```

##### Beancount 2.x

```python
CONFIG = [
    ECImporter(
        IBAN_NUMBER,
        'Assets:DKB:EC',
        currency='EUR',
        payee_patterns=[
            ('REWE', 'Expenses:Supermarket:REWE'),
            ('NETFLIX', 'Expenses:Online:Netflix'),
        ],
    ),
```

#### `CreditImporter`

`CreditImporter` accepts a `description_patterns` argument, which should be a list of
`(pattern, account)` tuples.

##### Beancount 3.x

```toml
[tool.beancount-dkb.credit]
card_number = "9999 9999 9999 9999"
account_name = "Assets:DKB:Credit"
currency = "EUR"
description_patterns=[
    ['REWE', 'Expenses:Supermarket:REWE'],
    ['NETFLIX', 'Expenses:Online:Netflix'],
]
```

##### Beancount 2.x

```python
CONFIG = [
    CreditImporter(
        CARD_NUMBER,
        'Assets:DKB:Credit',
        currency='EUR',
        description_patterns=[
            ('REWE', 'Expenses:Supermarket:REWE'),
            ('NETFLIX', 'Expenses:Online:Netflix'),
        ],
    )
```

## Contributing

Contributions are most welcome!

Please make sure you have Python 3.8+ and [Poetry] installed.

1. Clone the repository: `git clone https://github.com/siddhantgoel/beancount-dkb`
2. Install the packages required for development: `poetry install`
3. That's basically it. You should now be able to run the test suite: `poetry run task test`.

[Beancount]: http://furius.ca/beancount/
[DKB]: https://www.dkb.de
[Poetry]: https://python-poetry.org/
[changes documented here]: https://docs.google.com/document/d/1O42HgYQBQEna6YpobTqszSgTGnbRX7RdjmzR2xumfjs/edit#heading=h.hjzt0c6v8pfs
[config file]: https://beancount.github.io/docs/importing_external_data.html#configuration
[this guide]: https://beancount.github.io/docs/importing_external_data.html
