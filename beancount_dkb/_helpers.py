from contextlib import contextmanager
import locale


@contextmanager
def change_locale(key, value):
    original = locale.getlocale(key)

    try:
        locale.setlocale(key, value)
        yield
    finally:
        locale.setlocale(key, original)
