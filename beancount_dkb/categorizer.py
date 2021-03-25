import re
from beancount.core import data


class CategorizerProtocol:
    def categorize(self, entry):
        """"""


class PayeeCategorizer(CategorizerProtocol):
    def __init__(self, categories):
        self.categories = categories

    def categorize(self, entry):
        for category in self.categories:
            for payee in category['payees']:
                if re.match(payee, (entry.payee or entry.narration)):
                    entry.postings.append(
                        data.Posting(
                            category['account'], None, None, None, None, None,
                        )
                    )
                    return entry
        return entry


class DefaultCategorizer(CategorizerProtocol):
    def categorize(self, entry):
        return entry
