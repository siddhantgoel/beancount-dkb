Beancount DKB Importer
======================

.. image:: https://badge.fury.io/py/beancount-dkb.svg
    :target: https://pypi.python.org/pypi/beancount-dkb

.. image:: https://travis-ci.org/siddhantgoel/beancount-dkb.svg?branch=master
    :target: https://travis-ci.org/siddhantgoel/beancount-dkb

:code:`beancount-dkb` provides an Importer for converting CSV exports of
DKB_ (Deutsche Kredit Bank) account summaries to the Beancount_ format.

Installation
------------

.. code-block:: bash

    $ pip install beancount-dkb

Usage
-----

.. code-block:: python
    from beancount_dkb import ECImporter

    CONFIG = [
        ECImporter(IBAN, 'Assets:DKB:EC')
    ]

.. _Beancount: http://furius.ca/beancount/
.. _DKB: https://www.dkb.de/
