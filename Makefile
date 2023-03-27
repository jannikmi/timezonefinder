# https://stackoverflow.com/questions/38878088/activate-anaconda-python-environment-from-makefile
# By default make uses sh to execute commands, and sh doesn't know `source`
SHELL=/bin/bash


install:
	@echo "installing the development dependencies..."
	@#poetry install --no-dev
	@poetry install --extras "numba" --no-root --sync

update:
	@echo "pinning the dependencies specified in 'pyproject.toml':"
	@poetry update -vv
	#poetry export -f requirements.txt --output docs/requirements.txt --without-hashes


env:
	# conda env remove -n timezonefinder
	source $(CONDAROOT)/bin/activate && conda create -n timezonefinder python=3.7 poetry -y
	#	&& conda activate timezonefinder
	# && make req

parse:
	poetry run python ./scripts/file_converter.py -inp ./tmp/combined-with-oceans.json

data:
	bash parse_data.sh

test:
	@python ./runtests.py

hook:
	@pre-commit install
	@pre-commit run --all-files

hook2:
	@pre-commit autoupdate

hook3:
	@pre-commit clean

clean:
	rm -rf .pytest_cache .coverage coverage.xml tests/__pycache__ .mypyp_cache/ .tox


build:
	rm -r -f build
	pip install setuptools wheel
	python setup.py sdist bdist_wheel --python-tag py37.py38.py39.py310
	#python -m pip install build --user
	#python -m build --sdist --wheel --outdir dist/ .
	#poetry build

# documentation generation:
# https://docs.readthedocs.io/en/stable/intro/getting-started-with-sphinx.html
docs:
	(cd docs && make html)


.PHONY: clean test build docs
