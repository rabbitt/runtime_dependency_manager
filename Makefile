SHELL := bash
MAKEFLAGS += --no-print-directory --silent

# Variables
PACKAGE_NAME = runtime_dependency_manager
PYPI_REPO = pypi

# Commands
.PHONY: clean build tag publish test coverage htmlcov all

clean:
	rm -rf dist build $(PACKAGE_NAME).egg-info htmlcov .coverage $(PACKAGE_NAME)/version.py .version

build: clean
	python setup.py sdist bdist_wheel

get_version:
	scripts/get_version.sh > .version

tag: get_version
	@VERSION=$$(cat .version); \
	git tag -a v$$VERSION -m "Release $$VERSION"; \
	git push origin v$$VERSION

publish: build
	twine upload --repository $(PYPI_REPO) dist/*

test:
	coverage run -m unittest discover -s tests
	coverage report
	coverage html

all: tag publish
