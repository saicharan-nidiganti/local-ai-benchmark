# Development tasks. CI runs these same targets, so a green `make check` locally means the
# CI quality jobs should pass. Each recipe is a plain `uv` command: without make (for example
# in Windows PowerShell), run the command shown in the recipe. CONTRIBUTING.md lists them.

UV ?= uv
.DEFAULT_GOAL := help

.PHONY: help install lock-check lint format typecheck test check package clean

help: ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-11s %s\n", $$1, $$2}'

install: ## Install the locked dependencies and the dev tools
	$(UV) sync --frozen

lock-check: ## Fail if uv.lock is out of date with pyproject.toml
	$(UV) lock --check

lint: ## Ruff lint and format check
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format: ## Apply Ruff's fixes and formatting
	$(UV) run ruff check --fix .
	$(UV) run ruff format .

typecheck: ## mypy --strict over src
	$(UV) run mypy

test: ## Offline test suite with coverage (fails under 90%)
	$(UV) run python -m pytest --cov --cov-report=term

check: lint typecheck test ## Everything CI's quality jobs run

package: ## Build the sdist and wheel, then run the CLI from the wheel alone
	rm -rf dist
	$(UV) build
	$(UV) run --isolated --no-project --with dist/*.whl local-ai-benchmark --help
	$(UV) run --isolated --no-project --with dist/*.whl python -m local_ai_benchmark --help
	@echo "package check passed"

clean: ## Remove build, cache and coverage output
	rm -rf dist build .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
