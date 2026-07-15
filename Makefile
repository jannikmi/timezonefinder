# Makefile commands

# These targets are intended for local development on the timezonefinder project.

# Available targets:
#   install    - install all dependencies using uv sync for the current project
#   update     - update dependency pins and refresh pre-commit hooks
#   lock       - lock dependencies from pyproject.toml to uv.lock
#   force_update - force update dependencies by removing the lock file
#   outdated   - check for outdated packages excluding constrained dependencies
#   data       - regenerate timezone data under tmp with the full dataset
#   parse      - run the file converter on the downloaded combined dataset
#   testparse  - run the file converter on the test fixture JSON input
#   test       - execute unit tests excluding integration and slow tests
#   testint    - execute integration tests only
#   testall    - execute all tests including slow ones
#   speedtest  - run the timezone finding speed benchmark script
#   tox        - run tox for all configured environments
#   hook       - install and run pre-commit hooks on all files
#   hookup     - update pre-commit hooks, then update dependencies
#   hook3      - clean pre-commit hook state
#   clean      - remove build/test caches and tox artifacts
#   flatbuf    - compile FlatBuffers schemas to Python bindings
#   builsdist  - build a single source distribution tarball
#   build      - build wheels for supported Python versions
#   release    - tag the current commit with the version number and push it
#   rmtag      - remove the current version tag locally and remotely
#   docs       - build Sphinx HTML documentation from docs/

# https://stackoverflow.com/questions/38878088/activate-anaconda-python-environment-from-makefile
# By default make uses sh to execute commands, and sh doesn't know `source`
SHELL=/bin/bash

install:
	@echo "installing all specified dependencies..."
	# NOTE: root package needs to be installed for CLI tests to work!
	@uv sync --all-groups

update: hookup
	@echo "updating and pinning the dependencies specified in 'pyproject.toml':"
	@uv lock --upgrade

lock:
	@echo "locking the dependencies specified in 'pyproject.toml':"
	@uv lock


# when dependency resolving gets stuck:
force_update:
	@echo "force updating the requirements. removing lock file"
	@uv cache clean
	@rm -f uv.lock
	@echo "pinning the dependencies specified in 'pyproject.toml':"
	@uv sync --refresh

outdated:
	@echo "Checking for outdated packages (excluding those constrained by dependencies)..."
	@bash scripts/check_upgradeable.sh


data:
	rm -rf tmp
	bash update_data.sh --dataset=full --with-oceans

parse:
	uv run python ./scripts/file_converter.py -inp ./tmp/combined-with-oceans.json

testparse:
	uv run python ./scripts/file_converter.py -inp ./tests/test_input.json -out ./tmp/parsed_data

test:
# 	@uv run pytest
	@uv run pytest -m "not integration and not slow"

testint:
	@uv run pytest -m "integration"

# includes slow tests
testall:
	@uv run pytest

speedtest:
	# pytest -s flag: output to console
	uv run python scripts/check_speed_timezone_finding.py --rst
# 	@uv run pytest -s scripts/check_speed_timezone_finding.py::test_timezone_finding_speed -v
# 	@uv run pytest -s scripts/check_speed_initialisation.py -v

benchmarks: speedtest
	uv run python scripts/check_speed_initialisation.py --rst
	uv run python scripts/check_speed_inside_polygon.py --rst


reports: benchmarks
	uv run scripts/reporting.py

tox:
	@uv run tox

hook:
	@uv run pre-commit install
	@uv run pre-commit run --all-files

hookup:
	@echo "updating the pre-commit hooks..."
	@uv run pre-commit autoupdate

hook3:
	@uv run pre-commit clean

clean:
	rm -rf .pytest_cache .coverage coverage.xml tests/__pycache__ .mypyp_cache/ .tox

# compile flatbuffers files:
flatbuf:
	@echo "Compiling FlatBuffer schemas..."
	@flatc --python --gen-mutable -o . timezonefinder/flatbuf/schemas/polygons.fbs
	@flatc --python --gen-mutable -o . timezonefinder/flatbuf/schemas/hybrid_shortcuts_uint8.fbs
	@flatc --python --gen-mutable -o . timezonefinder/flatbuf/schemas/hybrid_shortcuts_uint16.fbs

builsdist:
	@echo "Building single tar.gz distribution..."
	uv build -v --sdist

build:
	rm -rf build dist
	uv build --python cp38
	uv build --python cp310
	uv build --python cp311
	uv build --python cp312
	uv build --python cp313

# in order to release a new package version, the commit needs to be tagged with the version number
# NOTE: do not skip the "non tag" GHA run, otherwise the CICD badge shows "failing"
# Push the release commit to origin before tagging; GitHub Actions uses the workflow file at the tagged SHA.
VERSION := $$(uv version --short)

release:
	@if [ "$$(git branch --show-current)" != "master" ]; then \
		echo "Error: releases can only be tagged from the master branch. Current branch: $$(git branch --show-current)"; \
		exit 1; \
	fi
	@echo "tagging the current commit with the version number: $(VERSION)"
	@git tag -a "$(VERSION)" -m "Release $(VERSION)"
	@echo "pushing the tag to the remote repository"
	@git push origin "$(VERSION)"

rmtag:
	@echo "removing the tag: $(VERSION)"
	@git tag -d "$(VERSION)"
	@echo "pushing the tag deletion to the remote repository"
	@git push origin --delete "$(VERSION)"

# documentation generation:
# https://docs.readthedocs.io/en/stable/intro/getting-started-with-sphinx.html
docs:
	(cd docs && make html)

.PHONY: clean test build docs
