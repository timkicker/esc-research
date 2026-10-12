# shortcut for linux and mac, the real entry point is uv run esc
.PHONY: install data parse build model all test lint clean-interim clean-all

install:
	uv sync --all-groups

data parse build model all test lint:
	uv run esc $@

clean-interim:
	uv run esc clean

clean-all:
	uv run esc clean-all
