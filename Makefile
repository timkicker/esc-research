.PHONY: install data parse build all test lint clean-interim clean-all

install:
	@echo ">> installing dependencies"
	uv sync --all-groups

data:
	@echo ">> fetching raw data into data/raw"
	uv run python -m esc.pipeline data

parse:
	@echo ">> parsing raw data into data/interim"
	uv run python -m esc.pipeline parse

build:
	@echo ">> building processed tables into data/processed"
	uv run python -m esc.pipeline build

all: data parse build
	@echo ">> pipeline finished"

test:
	@echo ">> running tests"
	uv run pytest -q

lint:
	@echo ">> linting"
	uv run ruff check src tests
	uv run ruff format --check src tests

clean-interim:
	@echo ">> removing data/interim"
	rm -rf data/interim

clean-all:
	@echo ">> removing data/raw data/interim data/processed cache"
	rm -rf data/raw data/interim data/processed cache
