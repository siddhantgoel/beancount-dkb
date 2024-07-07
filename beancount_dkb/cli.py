import sys
import tomllib
from pathlib import Path

from beangulp.testing import main as bg_main
from beancount_dkb import ECImporter, CreditImporter


_default_currency = "EUR"

_default_file_encoding = "ISO-8859-1"


def ec():
    config = _extract_config("ec")

    iban = config["iban"]
    account_name = config["account_name"]
    currency = config.get("currency", _default_currency)
    file_encoding = config.get("file_encoding", _default_file_encoding)
    meta_code = config.get("meta_code")
    payee_patterns = config.get("payee_patterns")
    description_patterns = config.get("description_patterns")

    importer = ECImporter(
        iban,
        account_name,
        currency=currency,
        file_encoding=file_encoding,
        meta_code=meta_code,
        payee_patterns=payee_patterns,
        description_patterns=description_patterns,
    )
    bg_main(importer)


def credit():
    config = _extract_config("credit")

    card_number = config["card_number"]
    account_name = config["account_name"]
    currency = config.get("currency", _default_currency)
    file_encoding = config.get("file_encoding", _default_file_encoding)
    description_patterns = config.get("description_patterns")

    importer = CreditImporter(
        card_number,
        account_name,
        currency=currency,
        file_encoding=file_encoding,
        description_patterns=description_patterns,
    )
    bg_main(importer)


def _extract_config(section: str) -> dict:
    pyproject = Path("pyproject.toml")

    if not pyproject.exists():
        print("pyproject.toml not found. Please run from the root of the repo.")
        sys.exit(1)

    with pyproject.open("rb") as fd:
        config = tomllib.load(fd)

    config_dkb = config.get("tool", {}).get("beancount-dkb")

    if not config_dkb:
        print("tool.beancount-dkb not found in pyproject.toml.")
        sys.exit(1)

    config_section = config_dkb.get(section)

    if not config_section:
        print(f"tool.beancount-dkb.{section} not found in pyproject.toml.")
        sys.exit(1)

    return config_section
