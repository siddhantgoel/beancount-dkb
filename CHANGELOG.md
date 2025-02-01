# CHANGELOG

## v1.5.0

- Fix support for Tagesgeld accounts (thanks [M4a1x])

## v1.4.0

- Fix number parsing for CSV exports from the updated banking interface
 - Balance values in credit exports are now assumed to have the en_US locale.
 - Balance/transaction values in credit/EC exports are assumed to have the de_DE locale.

## v1.3.0

- Support both `,` and `;` as delimiters for exports from the updated banking interface

## v1.2.0

- Parse balance values in credit card CSV exports metadata
- Update number parsing function to detect the current locale before parsing
- Enable support for Python 3.13
- Drop support for Python 3.8

## v1.1.0

- Replace `;` with `,` as the delimiter for CSV exports from the updated banking interface

## v1.0.0

- Add Beancount 3.x support (thus removing Beancount 2.x support)
- Add `beancount-dkb-ec` and `beancount-dkb-credit` CLI commands
- Rename `account` parameter to `account_name` (overlapping with the `account()` method
  definition required by `beangulp.importer.Importer`)
- Add Python 3.12 support

## v0.19.0

- Allow "€" instead of "EUR" in balance amounts (thanks [@e11bits])

## v0.18.0

- Promote v0.18.b2

## v0.18.0b2 (pre-release)

- Add back and deprecate `file_encoding` parameter for an easier transition

## v0.18.0b1 (pre-release)

- Support CSV exports from updated online banking interface introduced towards the end
  of year 2023
- Simplify file parsing
  - The importers now read all the lines in the file and treat the file contents before
    the header as metadata and after the header as transactional data.
- Remove `file_encoding` parameter
  - The older exports are always ISO-8859-1 encoded while the newer ones are UTF-8
    encoded (with a Byte order mark at the beginning).

## v0.17.0

- Support Tagesgeld accounts

## v0.16.0

- Support CSV files from new online banking interface
- Drop support for Python 3.7

## v0.15.0

- Allow pattern-matching transactions in `ECImporter` against description strings
- Enable support for Python 3.11

## v0.14.0

- Allow pattern-matching transactions in:
  - `ECImporter` (against payee strings) and,
  - `CreditImporter` (against description strings)

## v0.13.0

- Enable support for Python 3.10
- Drop support for Python 3.6

## v0.12.0

- Support additional credit card expected header format (thanks [Dr-Nuke])

## v0.11.0

- Use "Wertstellung" instead of "Belegdatum" for transaction dates in
  `CreditImporter` (thanks [@nils-werner])

## v0.10.0

- Add `meta_code` parameter to `ECImporter` (thanks [@bratekarate])

## v0.9.0

- Support credit data exports containing "Zeitraum" instead of "Von"/"Bis" dates
- Update `CreditImporter.file_date` return value (end date if the export
  contains start/end dates, otherwise the date of the export itself)

## v0.8.3

- Enable support for Python 3.9
- Drop support for Python 3.5

## v0.8.2

- Return date of last transaction from `file_date` for `CreditImporter`

## v0.8.1

- Add account number to narration if there's no transfer text (thanks [@tbm])
- Add optional parameter `existing_entries` to `extract()` (thanks [@tbm])

## v0.8.0

- Enable support for Python 3.8

## v0.7.1

- Fix parsing "Saldo" amounts in `CreditImporter` (#84)

## v0.7.0

- Replace `locale` based parsing of numbers with a simple helper function
- specifically for handling German formatting of numbers

## v0.6.4

- Add a `timedelta` of 1 day when setting the date on the `balance` directive
  outputs to make things consistent between what Beancount expects (balance
  amount valid from the beginning of the day) and what DKB exports contain
  (balance amount valid at the end of the day)

## v0.6.3

- Fix date value on `balance` that `ECImporter` outputs

## v0.6.2

- Support Python 3.7
- Implement `file_date` for `CreditImporter`
- Set `payee` in `CreditImporter` postings to `None` because of missing data
- Include additional assertions for matching dates in metadata entries in
  `ECImporter`

## v0.6.1

- Handle empty amount strings for `Tagessaldo` entries in `ECImporter` (thanks
  [@dmerkert])

## v0.6.0

- Emit closing `balance` directive based on the "Saldo" metadata entry
  (thanks [@dmerkert])

## v0.5.1

- Emit correct line numbers when constructing new metadata in `ECImporter`

## v0.5.0

- Differentiate between "Auftraggeber/Begünstigter" and "Verwendungszweck"
  (thanks [@niels])
- Implement `file_date` returning the closing date of the statement (thanks
  [@niels])
- Emit closing `balance` directive based on the "Kontostand vom" metadata
  entry (thanks [@niels])

## v0.4.0

- Ignore user-assigned account names in `ECImporter` (thanks [@niels])

## v0.3.1

- Support updated header format in `CreditImporter`

## v0.3.0

- Emit `balance` directive for `Tagessaldo` entries in `ECImporter`
- Remove unused `ignore_tagessaldo` parameter from `CreditImporter`

## v0.2.1

- Fix metadata keys in CreditImporter

## v0.2.0

- Added CreditImporter to import CSV exports of Credit Cards

## v0.1.0

- Added ECImporter to import CSV exports of EC accounts


[@Dr-Nuke]: https://github.com/Dr-Nuke
[@bratekarate]: https://githun.com/bratekarate
[@dmerkert]: https://github.com/dmerkert
[@e11bits]: https://github.com/e11bits
[@niels]: https://github.com/niels
[@nils-werner]: https://github.com/nils-werner
[@tbm]: https://github.com/tbm
[M4a1x]: https://github.com/M4a1x
