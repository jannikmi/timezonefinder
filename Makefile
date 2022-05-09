include .env

# https://stackoverflow.com/questions/38878088/activate-anaconda-python-environment-from-makefile
# By default make uses sh to execute commands, and sh doesn't know `source`
SHELL=/bin/bash


pin:
	@echo "pinning the dependencies specified in 'pyproject.toml':"
	@poetry update -vv
	#poetry export -f requirements.txt --output docs/requirements.txt --without-hashes

req:
	@echo "installing the development dependencies..."
	@poetry install --extras "numba" --no-root
	@#poetry install --no-dev


update: pin req

env:
	# conda env remove -n timezonefinder
	source $(CONDAROOT)/bin/activate && conda create -n timezonefinder python=3.7 poetry -y
	#	&& conda activate timezonefinder
	# && make req


test:
	@python ./runtests.py

hook:
	@pre-commit install
	@pre-commit run --all-files

hook2:
	@pre-commit autoupdate

clean:
	rm -rf .pytest_cache .coverage coverage.xml tests/__pycache__ .mypyp_cache/ .tox


build:
	rm -r -f build
	pip install setuptools wheel
	python setup.py sdist bdist_wheel --python-tag py37.py38.py39.py310
	#python -m pip install build --user
	#python -m build --sdist --wheel --outdir dist/ .
	#poetry build


.PHONY: clean test build
