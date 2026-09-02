.PHONY: help sync lint format test check run-demo run-ekartoteka test-e2e-ekartoteka

help:
	@echo "Available targets:"
	@echo "  make sync             Install and synchronize dependencies"
	@echo "  make lint             Run Ruff checks"
	@echo "  make format           Format Python code with Ruff"
	@echo "  make test             Run the test suite"
	@echo "  make check            Run lint and tests"
	@echo "  make run-demo         Run the demo integration"
	@echo "  make run-ekartoteka   Run e-Kartoteka using .env.ekartoteka"
	@echo "  make test-e2e-ekartoteka  Run read-only e-Kartoteka E2E tests"

sync:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .

test:
	uv run pytest

check: lint test

run-demo:
	uv run oblidog-integrations demo

run-ekartoteka:
	@test -f .env.ekartoteka || { echo "Missing .env.ekartoteka; copy .env.ekartoteka.example first."; exit 1; }
	@set -a; . ./.env.ekartoteka; set +a; uv run oblidog-integrations ekartoteka

test-e2e-ekartoteka:
	@test -f .env.ekartoteka || { echo "Missing .env.ekartoteka; copy .env.ekartoteka.example first."; exit 1; }
	@set -a; . ./.env.ekartoteka; set +a; uv run pytest -m ekartoteka_e2e
