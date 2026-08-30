"""The download guard on the unattended data update.

``update_data.sh`` runs from a weekly job whose pull request is merged and tagged
without a human reading it, so the archive it fetches is the last point at which a
truncated transfer or a replaced upstream asset can still be caught. These tests
exercise that check offline: the release API is mocked at the one function that
touches the network, which is what lets everything above it be tested at all.
"""

import json
from pathlib import Path

import pytest

from scripts.upstream_release import (
    UpstreamAsset,
    check_against_record,
    main,
    published_asset,
    read_record,
    release_tag,
    sha256_of,
    verify_archive,
    write_record,
)

ARCHIVE_NAME = "timezones-with-oceans.geojson.zip"
PAYLOAD = b"a timezone-boundary-builder release archive"
# the values the release API would publish for PAYLOAD
PAYLOAD_SIZE = len(PAYLOAD)
PAYLOAD_SHA256 = "a6581cf0be7b8937edfcdfb2e8e8ff1986abf5308d77f2c16758a77ec4fd7e31"


def _release(
    tag: str = "2026c",
    *,
    name: str = ARCHIVE_NAME,
    size: int | None = PAYLOAD_SIZE,
    digest: str | None = f"sha256:{PAYLOAD_SHA256}",
) -> dict:
    """A release description shaped like the GitHub API's."""
    asset: dict = {"name": name}
    if size is not None:
        asset["size"] = size
    if digest is not None:
        asset["digest"] = digest
    return {"tag_name": tag, "assets": [{"name": "timezone-names.json"}, asset]}


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    """A downloaded archive whose bytes match what ``_release`` publishes."""
    path = tmp_path / ARCHIVE_NAME
    path.write_bytes(PAYLOAD)
    return path


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch):
    """Answer every release API call with a given payload, and count the calls."""

    def serve(release: dict) -> None:
        monkeypatch.setattr(
            "scripts.upstream_release._read_url",
            lambda url: json.dumps(release).encode("utf-8"),
        )

    return serve


@pytest.mark.unit
def test_the_hash_is_taken_over_the_file_s_bytes(archive: Path) -> None:
    """The premise the whole guard rests on: the same function upstream states.

    ``PAYLOAD_SHA256`` is computed out of band, so this fails if the block-wise
    read drops or reorders anything - which nothing above it would notice, since
    every other test compares this function against itself.
    """
    assert sha256_of(archive) == PAYLOAD_SHA256


@pytest.mark.unit
def test_a_matching_download_verifies(archive: Path) -> None:
    verify_archive(archive, published_asset(_release(), ARCHIVE_NAME))


@pytest.mark.unit
def test_a_truncated_download_is_reported_as_a_size(archive: Path) -> None:
    """The likeliest failure, and the one whose byte count names its own cause."""
    archive.write_bytes(PAYLOAD[:-1])
    with pytest.raises(ValueError, match="bytes"):
        verify_archive(archive, published_asset(_release(), ARCHIVE_NAME))


@pytest.mark.unit
def test_different_bytes_of_the_same_length_are_caught(archive: Path) -> None:
    """A size check alone would pass this, which is why the hash is not optional."""
    archive.write_bytes(b"X" + PAYLOAD[1:])
    with pytest.raises(ValueError, match="hashes to"):
        verify_archive(archive, published_asset(_release(), ARCHIVE_NAME))


@pytest.mark.unit
def test_an_asset_without_a_digest_is_refused() -> None:
    """Unverifiable is a failure, not a warning.

    Downloading it anyway is precisely the unattended-publication gap this exists
    to close, and the manual fallback already exists.
    """
    with pytest.raises(ValueError, match="publishes no sha256 digest"):
        published_asset(_release(digest=None), ARCHIVE_NAME)


@pytest.mark.unit
def test_a_digest_in_another_algorithm_is_refused() -> None:
    with pytest.raises(ValueError, match="publishes no sha256 digest"):
        published_asset(
            _release(digest="md5:0cc175b9c0f1b6a831c399e269772661"), ARCHIVE_NAME
        )


@pytest.mark.unit
def test_an_asset_without_a_size_is_refused() -> None:
    with pytest.raises(ValueError, match="no byte size"):
        published_asset(_release(size=None), ARCHIVE_NAME)


@pytest.mark.unit
def test_a_missing_asset_names_what_the_release_does_publish() -> None:
    """The dataset variants differ only by asset name, so the list is the diagnosis."""
    with pytest.raises(ValueError, match="timezone-names.json"):
        published_asset(_release(), "timezones-now.geojson.zip")


@pytest.mark.unit
@pytest.mark.parametrize("tag", ["", "latest", "v2026c", "2026", None, 2026])
def test_a_tag_that_is_not_a_release_stops_the_run(tag: object) -> None:
    """Four downstream artefacts are named after the tag; none of them may guess."""
    with pytest.raises(ValueError, match="unexpected release tag"):
        release_tag({"tag_name": tag})


@pytest.mark.unit
def test_the_record_round_trips(tmp_path: Path) -> None:
    asset = UpstreamAsset(
        tag="2026c", asset=ARCHIVE_NAME, size=PAYLOAD_SIZE, sha256=PAYLOAD_SHA256
    )
    path = tmp_path / "DATA_SOURCE"
    write_record(path, asset)
    assert read_record(path) == asset


@pytest.mark.unit
def test_no_record_yet_is_not_an_error(tmp_path: Path) -> None:
    assert read_record(tmp_path / "DATA_SOURCE") is None


@pytest.mark.unit
@pytest.mark.parametrize(
    "text",
    [
        "tag: 2026c\nasset: a.zip\nsize: 1\n",
        "tag: 2026c\ntag: 2026b\nasset: a.zip\nsize: 1\nsha256: ab\n",
        "tag: 2026c\nasset: a.zip\nsize: 1\nsha256: ab\nextra: x\n",
        "tag: 2026c\nasset: a.zip\nsize: lots\nsha256: ab\n",
        "just a line\n",
    ],
    ids=["missing", "repeated", "unknown", "unparsable-size", "not-a-field"],
)
def test_an_unreadable_record_is_an_error(tmp_path: Path, text: str) -> None:
    """It guards the next update, so a record nobody can parse cannot be skipped."""
    path = tmp_path / "DATA_SOURCE"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        read_record(path)


@pytest.mark.unit
def test_an_asset_replaced_in_place_is_caught_by_the_record() -> None:
    """The one corruption the API digest cannot report, since it moves with the asset."""
    recorded = UpstreamAsset(
        tag="2026c", asset=ARCHIVE_NAME, size=PAYLOAD_SIZE, sha256=PAYLOAD_SHA256
    )
    republished = published_asset(_release(digest="sha256:" + "0" * 64), ARCHIVE_NAME)
    with pytest.raises(ValueError, match="replaced a released asset in place"):
        check_against_record(recorded, republished)


@pytest.mark.unit
@pytest.mark.parametrize("recorded_tag", ["2026b", "2026c"])
def test_the_record_only_speaks_about_the_tag_it_names(recorded_tag: str) -> None:
    """A new release is not a replaced asset; only the same tag can disagree."""
    recorded = UpstreamAsset(
        tag=recorded_tag, asset=ARCHIVE_NAME, size=PAYLOAD_SIZE, sha256=PAYLOAD_SHA256
    )
    check_against_record(recorded, published_asset(_release(), ARCHIVE_NAME))


@pytest.mark.unit
def test_verify_records_what_it_verified(archive: Path, api, tmp_path: Path) -> None:
    api(_release())
    record = tmp_path / "DATA_SOURCE"
    exit_code = main(
        [
            "verify",
            "--tag",
            "2026c",
            "--asset",
            ARCHIVE_NAME,
            "--archive",
            str(archive),
            "--record",
            str(record),
        ]
    )
    assert exit_code == 0
    assert read_record(record) == UpstreamAsset(
        tag="2026c", asset=ARCHIVE_NAME, size=PAYLOAD_SIZE, sha256=PAYLOAD_SHA256
    )


@pytest.mark.unit
def test_a_failed_verification_records_nothing(
    archive: Path, api, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Recording a digest the bytes never matched would launder the failure."""
    archive.write_bytes(PAYLOAD[:-1])
    api(_release())
    record = tmp_path / "DATA_SOURCE"
    exit_code = main(
        [
            "verify",
            "--tag",
            "2026c",
            "--asset",
            ARCHIVE_NAME,
            "--archive",
            str(archive),
            "--record",
            str(record),
        ]
    )
    assert exit_code == 1
    assert not record.exists()
    assert "bytes" in capsys.readouterr().err


@pytest.mark.unit
def test_resolve_tag_prints_the_bare_tag(api, capsys: pytest.CaptureFixture) -> None:
    """``update_data.sh`` names its download and DATA_VERSION from this stdout."""
    api(_release("2027a"))
    assert main(["resolve-tag"]) == 0
    assert capsys.readouterr().out == "2027a\n"
