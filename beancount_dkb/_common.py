from beancount.core.number import Decimal


class InvalidFormatError(Exception):
    pass


def fmt_number_de(value: str) -> Decimal:
    thousands_sep = '.'
    decimal_sep = ','

    return Decimal(value.replace(thousands_sep, '').replace(decimal_sep, '.'))
