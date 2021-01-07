# Beancount DKB Importer

[![image](https://github.com/siddhantgoel/beancount-dkb/workflows/beancount-dkb/badge.svg)](https://github.com/siddhantgoel/beancount-dkb/workflows/beancount-dkb/badge.svg)

[![image](https://img.shields.io/pypi/v/beancount-dkb.svg)](https://pypi.python.org/pypi/beancount-dkb)

[![image](https://img.shields.io/pypi/pyversions/beancount-dkb.svg)](https://pypi.python.org/pypi/beancount-dkb)

[![image](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

`beancount-dkb` provides an Importer for converting CSV exports of [DKB]
(Deutsche Kreditbank) account summaries to the [Beancount] format.

## Installation

```sh
$ pip install beancount-dkb
```

In case you prefer installing from the Github repository, please note that
`master` is the development branch so `stable` is what you should be installing
from.

## Usage

```python
from beancount_dkb import ECImporter, CreditImporter

IBAN_NUMBER = 'DE99 9999 9999 9999 9999 99' # your real IBAN number

CARD_NUMBER = '9999 9999 9999 9999'         # your real Credit Card number

CONFIG = [
    ECImporter(
        IBAN_NUMBER,
        'Assets:DKB:EC',
        currency='EUR',
        file_encoding='utf-8',
    ),

    CreditImporter(
        CARD_NUMBER,
        'Assets:DKB:Credit',
        currency='EUR',
        file_encoding='utf-8',
    )
]
```

## FAQ

```sh
ERROR:root:Importer beancount_dkb.ec.ECImporter.identify() raised an unexpected error: 'utf-8' codec can't decode byte 0xf6 in position 17: invalid start byte
```

Change the `file_encoding` parameter. It seems like the CSV
exports are `ISO-8859-1` encoded, but `utf-8`
seems like a useful default.

## Contributing

Contributions are most welcome!

Please make sure you have Python 3.6+ and [Poetry] installed.

1. Clone the repository: `git clone https://github.com/siddhantgoel/beancount-dkb`
2. Install the packages required for development: `poetry install`
3. That's basically it. You should now be able to run the test suite: `poetry run py.test`.

[DKB]: https://www.dkb.de
[Beancount]: http://furius.ca/beancount/
[Poetry]: https://python-poetry.org/
