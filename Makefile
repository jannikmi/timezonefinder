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
#   benchmark-fixtures - regenerate the committed, seeded benchmark input fixtures
#                        (already run by `data`/update_data.sh after a data update;
#                        run this directly only if just the fixtures need refreshing)
#   test       - execute unit tests excluding integration and slow tests
#   testint    - execute integration tests only
#   testall    - execute all tests including slow ones
#   speedtest  - run just the tracked core pytest-benchmark subset (quick, no JSON output)
#   benchmarks - run the full pytest-benchmark suite (benchmarks/), writing tmp/benchmark.json
#   benchmarks-ci - the exact core-subset measurement the benchmark CI workflow records
#   benchmark-noise - repeat benchmarks-ci on unchanged code and report the noise floor
#   reports    - benchmarks + render docs/benchmark_results_*.rst + the data report
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

# NOTE: `data` (update_data.sh) already regenerates these fixtures automatically
# since they are pinned to DATA_VERSION; only run this target directly when just
# the fixtures (not the boundary data) need refreshing.
benchmark-fixtures:
	uv run python -m scripts.generate_benchmark_fixtures

test:
# 	@uv run pytest
	@uv run pytest -m "not integration and not slow"

testint:
	@uv run pytest -m "integration"

# includes slow tests
testall:
	@uv run pytest

# path is relative to the repo root; tmp/ is already gitignored build/data scratch space
BENCHMARK_JSON := tmp/benchmark.json

# quick local sanity check: just the small, high-signal core subset, no JSON output
speedtest:
	uv run pytest benchmarks -m benchmark_core -v

# the full benchmark suite (all of benchmarks/), producing the JSON that
# scripts/render_benchmark_reports.py turns into docs/benchmark_results_*.rst.
# never combine with pytest-run-parallel's `--parallel-threads` (see CONTRIBUTING.md)
benchmarks:
	@mkdir -p tmp
	uv run pytest benchmarks -m benchmark --benchmark-json=$(BENCHMARK_JSON)

reports: benchmarks
	uv run python -m scripts.render_benchmark_reports --benchmark-json=$(BENCHMARK_JSON)
	uv run python -m scripts.reporting

# --- CI benchmarking (.github/workflows/benchmark.yml) ------------------------
# These paths/flags are declared here only; the workflow asks make for them
# (`make -s print-ci-benchmark-json`) instead of repeating the literals.

# raw pytest-benchmark output of the core subset, with the full statistics
RAW_CORE_BENCHMARK_JSON := tmp/benchmark-core-raw.json
# the report actually handed to benchmark-action/github-action-benchmark, with
# the tracked value rewritten from the mean to $(BENCHMARK_ESTIMATOR).
# Overridable on the command line so `benchmark-noise` can collect several runs.
CI_BENCHMARK_JSON := tmp/benchmark-core-tracked.json
# min is the least noise-sensitive estimator here - see scripts/benchmark_utils.py
BENCHMARK_ESTIMATOR := min
# enough rounds that pytest-benchmark's calibration has something to work with
# and the tracked min is drawn from a decent sample. The core subset is a few
# milliseconds per round, so this stays far below the CI time budget.
BENCHMARK_MIN_ROUNDS := 50
# the acceleration path CI tracks: what a plain `pip install timezonefinder`
# gives you. Numbers from the numba path are not comparable (see CONTRIBUTING.md).
BENCHMARK_ACCELERATION_PATH := clang
NOISE_RUNS_DIR := tmp/benchmark-noise
NOISE_RUNS := 5

print-ci-benchmark-json:
	@echo $(CI_BENCHMARK_JSON)

print-benchmark-acceleration-path:
	@echo $(BENCHMARK_ACCELERATION_PATH)

# the exact measurement CI records: core subset only, tracked estimator applied
benchmarks-ci:
	@mkdir -p $(dir $(CI_BENCHMARK_JSON))
	uv run pytest benchmarks -m benchmark_core \
		--benchmark-min-rounds=$(BENCHMARK_MIN_ROUNDS) \
		--benchmark-json=$(RAW_CORE_BENCHMARK_JSON)
	uv run python -m scripts.normalize_benchmark_json \
		--benchmark-json=$(RAW_CORE_BENCHMARK_JSON) \
		--output=$(CI_BENCHMARK_JSON) \
		--estimator=$(BENCHMARK_ESTIMATOR)

# repeat the CI measurement on unchanged code to characterise the noise floor.
# NOTE: locally this captures single-machine jitter only - the residual the
# same-runner pull request comparison has to clear. The trend chart's
# ALERT_THRESHOLD has to clear something much larger, the spread of the whole
# `ubuntu-latest` pool (several CPU models, up to ~1.58x on unchanged code);
# run the `benchmark` workflow via workflow_dispatch for the number that ships.
benchmark-noise:
	@rm -rf $(NOISE_RUNS_DIR)
	@mkdir -p $(NOISE_RUNS_DIR)
	@for i in $$(seq 1 $(NOISE_RUNS)); do \
		echo "--- noise run $$i/$(NOISE_RUNS) ---"; \
		$(MAKE) benchmarks-ci CI_BENCHMARK_JSON=$(NOISE_RUNS_DIR)/run-$$i.json || exit 1; \
	done
	uv run python -m scripts.benchmark_noise $(NOISE_RUNS_DIR)/run-*.json \
		--estimator=$(BENCHMARK_ESTIMATOR) --min-runs=$(NOISE_RUNS)

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
# NOTE: flatc derives the output path from the schema's namespace and writes an empty
# __init__.py at *every* level of it, overwriting existing ones. Generating with `-o .`
# therefore wiped the hand-maintained __all__ in timezonefinder/__init__.py,
# flatbuf/__init__.py and generated/__init__.py - the first of which is the whole public
# API. Generate into a scratch tree instead and copy back only the generated packages.
FLATBUF_GEN_DIR := tmp/flatbuf_generated
FLATBUF_PACKAGES := polygons shortcuts_uint8 shortcuts_uint16

flatbuf:
	@echo "Compiling FlatBuffer schemas..."
	@rm -rf $(FLATBUF_GEN_DIR)
	@mkdir -p $(FLATBUF_GEN_DIR)
	@flatc --python --gen-mutable -o $(FLATBUF_GEN_DIR) timezonefinder/flatbuf/schemas/polygons.fbs
	@flatc --python --gen-mutable -o $(FLATBUF_GEN_DIR) timezonefinder/flatbuf/schemas/hybrid_shortcuts_uint8.fbs
	@flatc --python --gen-mutable -o $(FLATBUF_GEN_DIR) timezonefinder/flatbuf/schemas/hybrid_shortcuts_uint16.fbs
	@cp -R $(addprefix $(FLATBUF_GEN_DIR)/timezonefinder/flatbuf/generated/,$(FLATBUF_PACKAGES)) \
		timezonefinder/flatbuf/generated/
	@rm -rf $(FLATBUF_GEN_DIR)
# The committed bindings are flatc output *after* the pre-commit pipeline (ruff-format
# collapses quotes, pyupgrade drops the redundant `object` base). Normalising here keeps
# `git diff` after this target readable - otherwise every file churns on formatting alone
# and a real codegen change is invisible. pre-commit exits non-zero when it fixes files.
	@uv run pre-commit run --files timezonefinder/flatbuf/generated/*/*.py > /dev/null || true
	@echo "Regenerated: $(FLATBUF_PACKAGES)"

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

.PHONY: clean test testint testall build docs speedtest benchmarks reports \
	benchmarks-ci benchmark-noise print-ci-benchmark-json \
	print-benchmark-acceleration-path
