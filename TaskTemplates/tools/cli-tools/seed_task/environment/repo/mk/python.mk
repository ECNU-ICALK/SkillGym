.PHONY: all-dev python-init python-tests cli-smoke-tests check

all-dev: python-init ## Install local development dependencies.

python-init: $(PY_BOOTSTRAP) ## Install local Python test dependencies.

$(PY_BOOTSTRAP):
	mkdir -p $(PY_DEPS_DIR)
	$(PYTHON) -m pip install --upgrade --target $(PY_DEPS_DIR) "pytest>=8,<9"
	touch $(PY_BOOTSTRAP)

python-tests: ## Run Python unit tests.
	$(PYTHON) -m pytest -q

cli-smoke-tests: ## Run CLI smoke tests from the source tree.
	$(PYTHON) tests/smoke_cli.py

check: python-tests cli-smoke-tests package packaged-smoke ## Run the full local validation workflow.
