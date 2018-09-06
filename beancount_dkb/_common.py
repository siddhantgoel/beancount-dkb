import locale
from contextlib import contextmanager


class InvalidFormatError(Exception):
    pass


@contextmanager
def change_locale(key, value):
    original = locale.getlocale(key)

    try:
        locale.setlocale(key, value)
        yield
    finally:
        locale.setlocale(key, original)
