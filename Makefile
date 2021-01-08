lint-black:
	poetry run black --check beancount_dkb/ tests/

lint-flake8:
	poetry run flake8 beancount_dkb/ tests/

test-pytest:
	poetry run pytest tests/
