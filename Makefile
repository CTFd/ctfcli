lint:
	black --diff .
	isort --check .
	ruff check .

format:
	black .
	isort .
	ruff --fix .

test:
	pytest --cov=ctfcli tests

clean:
	rm -rf dist/
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	rm -f .coverage
