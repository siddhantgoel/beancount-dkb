CHANGELOG
=========

v0.6.1
------
- Handle empty amount strings for :code:`Tagessaldo` entries in
  :code:`ECImporter` (thanks `@dmerkert`_)

v0.6.0
------
- Emit closing :code:`balance` directive based on the "Saldo" metadata entry
  (thanks `@dmerkert`_)

v0.5.1
------
- Emit correct line numbers when constructing new metadata in :code:`ECImporter`

v0.5.0
------

- Differentiate between "Auftraggeber/Begünstigter" and "Verwendungszweck"
  (thanks `@niels`_)
- Implement :code:`file_date` returning the closing date of the statement
  (thanks `@niels`_)
- Emit closing :code:`balance` directive based on the "Kontostand vom" metadata
  entry (thanks `@niels`_)

v0.4.0
------

- Ignore user-assigned account names in :code:`ECImporter` (thanks `@niels`_)

v0.3.1
------

- Support updated header format in :code:`CreditImporter`

v0.3.0
------

- Emit :code:`balance` directive for :code:`Tagessaldo` entries in
  :code:`ECImporter`
- Remove unused :code:`ignore_tagessaldo` parameter from :code:`CreditImporter`

v0.2.1
------

- Fix metadata keys in CreditImporter

v0.2.0
------

- Added CreditImporter to import CSV exports of Credit Cards

v0.1.0
------

- Added ECImporter to import CSV exports of EC accounts


.. _@niels: https://github.com/niels
.. _@dmerkert: https://github.com/dmerkert
