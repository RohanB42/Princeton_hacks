.PHONY: setup setup-science lint format format-check test import-check fixture data-check data-smoke
setup:
	poetry sync
setup-science:
	poetry sync --with science
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
fixture:
	poetry run python -m oligo_engine --config configs/fixture.toml --output artifacts/fixture
data-check:
	poetry run python -m oligo_engine.collection --validate
data-smoke:
	poetry run python -m oligo_engine.collection --config configs/all-datasets-smoke.toml --output artifacts/collection-smoke
