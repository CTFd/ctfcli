lint:
	ruff check --ignore=E402,E501,E712,I002 --exclude=ctfcli/templates --exclude=build .
	black --check --exclude=ctfcli/templates .

format:
	black --exclude=ctfcli/templates .

install:
	python3 setup.py install

build:
	python3 setup.py sdist bdist_wheel

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf ctfcli.egg-info/

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