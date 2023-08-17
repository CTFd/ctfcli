lint:
	black --check .
	isort --check .
	ruff check .

format:
	black .
	isort .
	ruff --fix .

test:
	green tests -r

install:
	python3 setup.py install

build:
	python3 setup.py sdist bdist_wheel

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf ctfcli.egg-info/
	rm -rf .ruff_cache
	rm -f .coverage

publish-test:
	@echo "Publishing to TestPyPI"
	@echo "Are you sure? [y/N] " && read ans && [ $${ans:-N} == y ]
	python3 setup.py sdist bdist_wheel
	twine upload --repository test dist/*

publish-pypi:
	@echo "Publishing to PyPI"
	@echo "ARE YOU ABSOLUTELY SURE? [y/N] " && read ans && [ $${ans:-N} == y ]
	python3 setup.py sdist bdist_wheel
	twine upload --repository pypi dist/*
