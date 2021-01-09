fmt-black:
	poetry run black beancount_dkb/ tests/

# lint

lint: lint-black lint-flake8

lint-black:
	poetry run black --check beancount_dkb/ tests/

lint-flake8:
	poetry run flake8 beancount_dkb/ tests/

# test

test-pytest:
	poetry run pytest tests/
