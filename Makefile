.PHONY: install sync lint format test hooks check

install: sync hooks

sync:
	uv sync --all-groups

hooks:
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest

check: lint test

commit:
	uv run cz commit
