CHANGELOG
=========

v0.8.3
------
- Enable support for Python 3.9
- Drop support for Python 3.5

v0.8.2
------
- Return date of last transaction from :code:`file_date` for :code:`CreditImporter`

v0.8.1
------
- Add account number to narration if there's no transfer text (thanks `@tbm`_)
- Add optional parameter :code:`existing_entries` to :code:`extract()` (thanks `@tbm`_)

v0.8.0
------
- Enable support for Python 3.8

v0.7.1
------
- Fix parsing "Saldo" amounts in :code:`CreditImporter` (#84)

v0.7.0
------
- Replace :code:`locale` based parsing of numbers with a simple helper function
  specifically for handling German formatting of numbers

v0.6.4
------
- Add a :code:`timedelta` of 1 day when setting the date on the :code:`balance`
  directive outputs to make things consistent between what Beancount expects
  (balance amount valid from the beginning of the day) and what DKB exports
  contain (balance amount valid at the end of the day)

v0.6.3
------
- Fix date value on :code:`balance` that :code:`ECImporter` outputs

v0.6.2
------
- Support Python 3.7
- Implement :code:`file_date` for :code:`CreditImporter`
- Set :code:`payee` in :code:`CreditImporter` postings to :code:`None` because of missing data
- Include additional assertions for matching dates in metadata entries in :code:`ECImporter`

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


.. _@dmerkert: https://github.com/dmerkert
.. _@niels: https://github.com/niels
.. _@tbm: https://github.com/tbm
