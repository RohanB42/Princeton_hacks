.PHONY: setup setup-science setup-molecular molecular-test molecular-fixture lint format format-check test import-check fixture data-check data-smoke
setup:
	poetry sync
setup-science:
	poetry sync --with science
setup-molecular:
	poetry sync --with science,molecular-rl,molecular-data
molecular-test:
	poetry run pytest -q tests/test_molecular_design.py tests/test_molecular_rl_optional.py
molecular-fixture:
	poetry run python -m oligo_engine.molecular_design compare --config configs/molecular-design/fixture.json --output artifacts/molecular-fixture
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
