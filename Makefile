.PHONY: all
.IGNORE: lint format

lint:
	ruff format --check .
	ruff check .

format:
	ruff check --select F401 --select TID252 --select I --fix .
	ruff format .

test:
	pytest --cov=ctfcli tests

clean:
	rm -rf dist/
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	rm -f .coverage
