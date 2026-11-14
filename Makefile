.PHONY: setup lint format format-check test import-check
setup:
	poetry sync
lint:
	poetry run ruff check .
format:
	poetry run ruff format .
format-check:
	poetry run ruff format --check .
test:
	poetry run pytest
import-check:
	poetry run python -c "import oligo_engine"
