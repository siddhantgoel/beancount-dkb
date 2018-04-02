import locale

from beancount.ingest import importer

from ._helpers import change_locale


class DKBECImporter(importer.ImporterProtocol):
    def __init__(self, iban, account, currency='EUR', ignore_tagessaldo=True,
                 numeric_locale='de_DE.UTF-8', file_encoding='ISO-8859-1'):
        self.iban = iban
        self.account = account
        self.currency = currency
        self.ignore_tagessaldo = ignore_tagessaldo
        self.numeric_locale = numeric_locale
        self.file_encoding = file_encoding

    def file_account(self, _):
        return self.account

    def identify(self, file_):
        header = '"Kontonummer:";"{} / Girokonto";'.format(self.iban)

        return file_.head().startswith(header)

    def extract(self, file_):
        with change_locale(locale.LC_NUMERIC, self.numeric_locale):
            return []
