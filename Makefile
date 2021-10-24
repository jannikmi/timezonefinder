
pin:
	@echo "pinning the dependencies specified in 'pyproject.toml':"
	@poetry update

req:
	@echo "installing the development dependencies..."
	@poetry install --extras "numba"
	@#poetry install --no-dev

update: pin req

test:
	@python ./runtests.py

hook:
	@pre-commit install
	@pre-commit run --all-files

hook2:
	@pre-commit autoupdate

clean:
	rm -rf .pytest_cache .coverage coverage.xml tests/__pycache__ .mypyp_cache/ .tox


.PHONY: clean test
