Beancount DKB Importer
======================

.. image:: https://img.shields.io/pypi/v/beancount-dkb.svg
    :target: https://pypi.python.org/pypi/beancount-dkb

.. image:: https://travis-ci.org/siddhantgoel/beancount-dkb.svg?branch=stable
    :target: https://travis-ci.org/siddhantgoel/beancount-dkb

:code:`beancount-dkb` provides an Importer for converting CSV exports of
DKB_ (Deutsche Kredit Bank) account summaries to the Beancount_ format.

Installation
------------

.. code-block:: bash

    $ pip install beancount-dkb

In case you prefer installing from the Github repository, please note that
:code:`master` is the development branch so :code:`stable` is what you should be
installing from.

Usage
-----

.. code-block:: python

    from beancount_dkb import ECImporter, CreditImporter

    CONFIG = [
        ECImporter(
            IBAN_NUMBER, 'Assets:DKB:EC',
            currency='EUR',
            numeric_locale='de_DE.UTF-8',
            file_encoding='utf-8',
        ),

        CreditImporter(
            CARD_NUMBER, 'Assets:DKB:Credit',
            currency='EUR',
            numeric_locale='de_DE.UTF-8',
            file_encoding='utf-8',
        )
    ]

FAQ
---

.. code-block:: bash

    ERROR:root:Importer beancount_dkb.ec.ECImporter.identify() raised an unexpected error: 'utf-8' codec can't decode byte 0xf6 in position 17: invalid start byte

Change the :code:`file_encoding` parameter. It seems like the CSV exports are
:code:`ISO-8859-1` encoded, but :code:`utf-8` seems like a useful default.

Contributing
------------

Contributions are most welcome!

Please make sure you have Python 3.5+ and Poetry_ installed.

1. Git clone the repository -
   :code:`git clone https://github.com/siddhantgoel/beancount-dkb`

2. Install the packages required for development -
   :code:`poetry install`

3. That's basically it. You should now be able to run the test suite -
   :code:`poetry run py.test`.

.. _Beancount: http://furius.ca/beancount/
.. _DKB: https://www.dkb.de/
.. _Poetry: https://poetry.eustace.io/
