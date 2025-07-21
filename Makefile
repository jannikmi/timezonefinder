# https://stackoverflow.com/questions/38878088/activate-anaconda-python-environment-from-makefile
# By default make uses sh to execute commands, and sh doesn't know `source`
SHELL=/bin/bash

install:
	pip install --upgrade pip
	@echo "installing all specified dependencies..."
	# NOTE: root package needs to be installed for CLI tests to work!
	@uv sync --all-groups

update:
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
	@uv pip list --outdated


env:
	# conda env remove -n timezonefinder
	source $(CONDAROOT)/bin/activate && conda create -n timezonefinder python=3.9 uv -y
	#	&& conda activate timezonefinder
	# && make req

parse:
	uv run python ./scripts/file_converter.py -inp ./tmp/combined-with-oceans.json

data:
	bash parse_data.sh

test:
	@uv run pytest
# 	@uv run pytest -m "integration"
# 	@uv run pytest -m "not integration"

tox:
	@uv run tox

hook:
	@uv run pre-commit install
	@uv run pre-commit run --all-files

hookup:
	@uv run pre-commit autoupdate

hook3:
	@uv run pre-commit clean

clean:
	rm -rf .pytest_cache .coverage coverage.xml tests/__pycache__ .mypyp_cache/ .tox

# compile flatbuffers files:
flatbuf:
	@echo "Compiling FlatBuffer schemas..."
	@flatc --python --gen-mutable timezonefinder/flatbuf/polygon_schema.fbs
	@flatc --python --gen-mutable timezonefinder/flatbuf/shortcut_schema.fbs

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
release:
	@echo "tagging the current commit with the version number: $(VERSION)"
	git tag -a "$(shell uv version --short)" -m "Release $(VERSION)"
	@echo "pushing the changes to the remote repository"
	git push origin "$(shell uv version --short)"

rmtag:
	@echo "removing the tag: $(VERSION)"
	git tag -d "$(shell uv version --short)"
	@echo "pushing the changes to the remote repository"
	git push origin --delete "$(shell uv version --short)"

# documentation generation:
# https://docs.readthedocs.io/en/stable/intro/getting-started-with-sphinx.html
docs:
	(cd docs && make html)

speedtest:
	# pytest -s flag: output to console
	@uv run pytest -s scripts/check_speed_timezone_finding.py::test_timezone_finding_speed -v
# 	@uv run pytest -s scripts/check_speed_initialisation.py -v

.PHONY: clean test build docs
