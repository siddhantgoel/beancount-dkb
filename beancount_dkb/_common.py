from contextlib import contextmanager
import locale


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
