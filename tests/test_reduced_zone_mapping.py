"""The vendored upstream lookup of which zones the reduced dataset merges.

``update_data.sh --dataset=same-since-now`` compiles the reduced ``timezones-now``
data, in which zones that keep the same time from now on are one zone under one
representative name. The expectations in :mod:`tests.locations` name zones of the full
dataset, so a checkout carrying reduced data needs to know what each of them became -
and the standing decision is that such a table comes from upstream or not at all,
because a hand-curated one makes timezone answers depend on somebody's judgement.

These tests are what makes "from upstream" checkable rather than merely intended: the
committed bytes are re-hashed against the digest the release API published for them,
so a table edited by hand fails here instead of quietly deciding what a zone is.
"""

import pytest

from scripts.configs import (
    REDUCED_ZONE_MAPPING_ASSET,
    REDUCED_ZONE_MAPPING_FILE,
    REDUCED_ZONE_SOURCE_FILE,
    read_data_version,
)
from scripts.upstream_release import UpstreamAsset, read_record, sha256_of
from tests import auxiliaries
from tests.auxiliaries import (
    convert_to_reduced_timezone,
    packaged_dataset_is_reduced,
    reduced_zone_representatives,
    single_location_test,
)
from tests.locations import TEST_LOCATIONS
from timezonefinder.configs import DEFAULT_DATA_DIR
from timezonefinder.zone_names import read_zone_names


@pytest.fixture
def record() -> UpstreamAsset:
    """What the vendored copy says it is."""
    recorded = read_record(REDUCED_ZONE_SOURCE_FILE)
    assert recorded is not None, f"{REDUCED_ZONE_SOURCE_FILE} is missing"
    return recorded


@pytest.fixture
def reduced_dataset(monkeypatch: pytest.MonkeyPatch):
    """Answer as a checkout that compiled the reduced dataset would.

    The alternative is compiling it, which is a 26 MB download and a full converter
    run for a question about names. What the detection actually reads is the packaged
    zone-name list, and under reduced data that list is the representatives.
    """
    representatives = sorted(set(reduced_zone_representatives().values()))
    monkeypatch.setattr(auxiliaries, "read_zone_names", lambda path: representatives)
    packaged_dataset_is_reduced.cache_clear()
    yield
    packaged_dataset_is_reduced.cache_clear()


@pytest.mark.unit
def test_the_vendored_bytes_are_the_ones_upstream_released(
    record: UpstreamAsset,
) -> None:
    """The whole point of vendoring rather than deriving.

    A digest over the committed file is the only thing that can tell an upstream
    table from one somebody extended by hand, and this is the one check that would
    fail if the mapping were ever edited in place - including by a formatter, which
    is why .pre-commit-config.yaml exempts this file from the JSON and newline hooks.
    """
    assert REDUCED_ZONE_MAPPING_FILE.stat().st_size == record.size
    assert sha256_of(REDUCED_ZONE_MAPPING_FILE) == record.sha256


@pytest.mark.unit
def test_the_mapping_describes_the_packaged_release(record: UpstreamAsset) -> None:
    """A mapping from another release would merge zones this data does not merge."""
    assert record.tag == read_data_version()
    assert record.asset == REDUCED_ZONE_MAPPING_ASSET


@pytest.mark.unit
def test_every_representative_names_itself() -> None:
    """Converting a name the reduced dataset already uses has to be a no-op.

    Upstream lists the representative among the zones merged into it, so the inverted
    table maps it to itself; without that the conversion would not be idempotent and
    an expectation already written in reduced terms would be rewritten to nothing.
    """
    representatives = reduced_zone_representatives()
    for representative in set(representatives.values()):
        assert representatives[representative] == representative


@pytest.mark.unit
def test_every_representative_is_a_zone_of_the_full_dataset() -> None:
    """The reduced dataset renames nothing: it only merges.

    So each representative is a name the packaged full dataset also carries. A
    representative that is not would mean the table describes a different dataset
    than the one the expectations are written against.
    """
    packaged = set(read_zone_names(DEFAULT_DATA_DIR))
    assert set(reduced_zone_representatives().values()) <= packaged


@pytest.mark.unit
def test_every_expectation_the_suite_asserts_is_covered() -> None:
    """A location expectation the table does not name would survive unconverted.

    That is the silent half of the failure mode: the assertion then compares a
    full-dataset name against reduced data and reports a wrong answer rather than a
    missing mapping entry.
    """
    expectations = {expected for _, _, _, expected in TEST_LOCATIONS}
    assert expectations <= set(reduced_zone_representatives())


@pytest.mark.unit
def test_the_packaged_full_dataset_converts_to_itself() -> None:
    """What every ordinary run does: nothing.

    The conversion is gated on the packaged data because applying it unconditionally
    would rewrite ``Europe/Berlin`` to ``Europe/Paris`` against data that answers
    ``Europe/Berlin`` - which is why the original helper was left commented out.
    """
    assert not packaged_dataset_is_reduced()
    for _, _, _, expected in TEST_LOCATIONS:
        assert convert_to_reduced_timezone(expected) == expected


@pytest.mark.unit
def test_reduced_data_is_detected_and_expectations_are_merged(
    reduced_dataset: None,
) -> None:
    assert packaged_dataset_is_reduced()
    assert convert_to_reduced_timezone("Europe/Berlin") == "Europe/Paris"
    assert convert_to_reduced_timezone("Europe/Paris") == "Europe/Paris"


@pytest.mark.unit
def test_a_zone_upstream_does_not_map_is_left_alone(reduced_dataset: None) -> None:
    """Upstream's table omits ``Etc/GMT+12``, which the full dataset does carry.

    Returning it unchanged makes the assertion fail on the name the expectation
    holds; a lookup that raised would fail inside the helper instead, hiding which
    location was being checked.
    """
    assert "Etc/GMT+12" in read_zone_names(DEFAULT_DATA_DIR)
    assert "Etc/GMT+12" not in reduced_zone_representatives()
    assert convert_to_reduced_timezone("Etc/GMT+12") == "Etc/GMT+12"


@pytest.mark.unit
def test_the_assertion_helper_expects_the_merged_name(reduced_dataset: None) -> None:
    """The consumer, and the reason the table is in the tree at all."""

    def timezone_at(lng: float, lat: float) -> str:
        return "Europe/Paris"

    single_location_test(timezone_at, 52.5, 13.4, "Berlin", "Europe/Berlin")

    def wrong(lng: float, lat: float) -> str:
        return "Europe/Berlin"

    with pytest.raises(AssertionError, match="Europe/Berlin merged"):
        single_location_test(wrong, 52.5, 13.4, "Berlin", "Europe/Berlin")
