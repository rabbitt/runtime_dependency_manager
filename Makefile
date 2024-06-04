# runtime_dependency_manager
# Copyright (C) 2024 Carl Corliss
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

SHELL := bash
MAKEFLAGS += --no-print-directory --silent

# Variables
PACKAGE_NAME = runtime_dependency_manager
PYPI_REPO = pypi

# Commands
.PHONY: clean build tag publish test coverage htmlcov all

all: test tag publish

clean:
	rm -rf dist build $(PACKAGE_NAME).egg-info htmlcov .coverage $(PACKAGE_NAME)/version.py .version

build: clean
	python setup.py sdist bdist_wheel

get_version:
	scripts/get_version.sh > .version

check_git_clean:
	@if ! git diff-index --quiet HEAD --; then \
		echo "Error: Working directory is not clean. Please commit or stash your changes."; \
		exit 1; \
	fi

tag: check_git_clean get_version
	@VERSION=$$(cat .version); \
	git tag -a v$$VERSION -m "Release $$VERSION"; \
	git push origin v$$VERSION

publish: build
	twine upload --repository $(PYPI_REPO) dist/*

test:
	coverage run -m unittest discover -s tests
	coverage report
	coverage html

