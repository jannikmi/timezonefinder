"""The download guard on the unattended data update.

``update_data.sh`` runs from a weekly job whose pull request is merged and tagged
without a human reading it, so the archive it fetches is the last point at which a
truncated transfer or a replaced upstream asset can still be caught. These tests
exercise that check offline: the release API is mocked at the one function that
touches the network, which is what lets everything above it be tested at all.
"""

import json
import http.client
import urllib.error
from email.message import Message
from pathlib import Path

import pytest

from scripts.upstream_release import (
    RETRY_ATTEMPTS,
    TOKEN_VARIABLES,
    UpstreamAsset,
    _read_url,
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


def _verify_argv(archive: Path, *, record: Path, stage: Path | None) -> list[str]:
    argv = [
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
    if stage is not None:
        argv += ["--stage", str(stage)]
    return argv


@pytest.mark.unit
def test_verify_stages_what_it_verified(archive: Path, api, tmp_path: Path) -> None:
    api(_release())
    stage = tmp_path / "staged"
    assert (
        main(_verify_argv(archive, record=tmp_path / "DATA_SOURCE", stage=stage)) == 0
    )
    assert read_record(stage) == UpstreamAsset(
        tag="2026c", asset=ARCHIVE_NAME, size=PAYLOAD_SIZE, sha256=PAYLOAD_SHA256
    )


@pytest.mark.unit
def test_verify_does_not_install_the_record_itself(
    archive: Path, api, tmp_path: Path
) -> None:
    """The two stamps have to advance together, and the parse sits between them.

    ``update_data.sh`` installs the staged record next to ``DATA_VERSION`` only once
    the converter has succeeded. Writing it here instead would leave a run that
    failed in between describing an upstream release the packaged data is not - which
    ``tests/test_data_version.py`` then reports as drift rather than as a failed run.
    """
    api(_release())
    record = tmp_path / "DATA_SOURCE"
    record.write_text(
        UpstreamAsset(
            tag="2026b", asset=ARCHIVE_NAME, size=1, sha256="ab" * 32
        ).render(),
        encoding="utf-8",
    )
    assert main(_verify_argv(archive, record=record, stage=tmp_path / "staged")) == 0
    untouched = read_record(record)
    assert untouched is not None and untouched.tag == "2026b"


@pytest.mark.unit
def test_verify_without_a_stage_writes_nothing(
    archive: Path, api, tmp_path: Path
) -> None:
    """Verification on its own is a question, not an edit."""
    api(_release())
    assert main(_verify_argv(archive, record=tmp_path / "DATA_SOURCE", stage=None)) == 0
    assert list(tmp_path.iterdir()) == [archive]


@pytest.mark.unit
def test_a_failed_verification_records_nothing(
    archive: Path, api, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Recording a digest the bytes never matched would launder the failure."""
    archive.write_bytes(PAYLOAD[:-1])
    api(_release())
    stage = tmp_path / "staged"
    exit_code = main(
        _verify_argv(archive, record=tmp_path / "DATA_SOURCE", stage=stage)
    )
    assert exit_code == 1
    assert not stage.exists()
    assert "bytes" in capsys.readouterr().err


@pytest.mark.unit
def test_resolve_tag_prints_the_bare_tag(api, capsys: pytest.CaptureFixture) -> None:
    """``update_data.sh`` names its download and DATA_VERSION from this stdout."""
    api(_release("2027a"))
    assert main(["resolve-tag"]) == 0
    assert capsys.readouterr().out == "2027a\n"


@pytest.fixture
def no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """A clean environment, so a real one on the machine cannot decide these."""
    for name in TOKEN_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://api.github.com/x", code, "Unauthorized", Message(), None
    )


@pytest.mark.unit
@pytest.mark.parametrize("variable", TOKEN_VARIABLES)
def test_a_rejected_token_falls_back_to_an_unauthenticated_read(
    monkeypatch: pytest.MonkeyPatch, no_token: None, variable: str
) -> None:
    """A stale token in a shell must not fail a request that needs no token.

    The release API is public, so the only thing authentication buys here is quota -
    and a developer with an expired ``GITHUB_TOKEN`` exported for other tooling would
    otherwise get a 401 on an endpoint ``curl`` had always read anonymously.
    """
    monkeypatch.setenv(variable, "expired")
    seen: list[str | None] = []

    def request(url: str, token: str | None) -> bytes:
        seen.append(token)
        if token is not None:
            raise _http_error(401)
        return b"{}"

    monkeypatch.setattr("scripts.upstream_release._request", request)
    assert _read_url("https://api.github.com/x") == b"{}"
    assert seen == ["expired", None]


@pytest.mark.unit
def test_a_rate_limited_token_is_not_retried_anonymously(
    monkeypatch: pytest.MonkeyPatch, no_token: None
) -> None:
    """403 with a token is the rate limit, and the anonymous limit is stricter.

    Retrying would replace a diagnosis the maintainer can act on with a second
    failure against a lower quota.
    """
    monkeypatch.setenv("GH_TOKEN", "valid")
    attempts = 0

    def request(url: str, token: str | None) -> bytes:
        nonlocal attempts
        attempts += 1
        raise _http_error(403)

    monkeypatch.setattr("scripts.upstream_release._request", request)
    with pytest.raises(urllib.error.HTTPError):
        _read_url("https://api.github.com/x")
    assert attempts == 1


@pytest.mark.unit
def test_no_token_means_one_anonymous_read(
    monkeypatch: pytest.MonkeyPatch, no_token: None
) -> None:
    seen: list[str | None] = []

    def request(url: str, token: str | None) -> bytes:
        seen.append(token)
        return b"{}"

    monkeypatch.setattr("scripts.upstream_release._request", request)
    assert _read_url("https://api.github.com/x") == b"{}"
    assert seen == [None]


@pytest.fixture
def instant_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retry without paying the wait, so the tests below stay sub-millisecond."""
    monkeypatch.setattr("scripts.upstream_release._sleep", lambda seconds: None)


@pytest.mark.unit
@pytest.mark.parametrize("code", [500, 502, 503, 429])
def test_a_transient_failure_is_retried(
    monkeypatch: pytest.MonkeyPatch, no_token: None, instant_backoff: None, code: int
) -> None:
    """The weekly update is unattended, so a blip must not cost a maintenance issue.

    This replaced a `curl --retry 3`, and dropping the retries would have made a
    one-second 503 during either release lookup abort an otherwise valid update.
    """
    attempts = 0

    def request(url: str, token: str | None) -> bytes:
        nonlocal attempts
        attempts += 1
        if attempts < RETRY_ATTEMPTS:
            raise _http_error(code)
        return b"{}"

    monkeypatch.setattr("scripts.upstream_release._request", request)
    assert _read_url("https://api.github.com/x") == b"{}"
    assert attempts == RETRY_ATTEMPTS


@pytest.mark.unit
def test_a_transport_error_without_a_status_is_retried(
    monkeypatch: pytest.MonkeyPatch, no_token: None, instant_backoff: None
) -> None:
    """A reset connection or DNS hiccup carries no HTTP status at all."""
    attempts = 0

    def request(url: str, token: str | None) -> bytes:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise urllib.error.URLError("connection reset by peer")
        return b"{}"

    monkeypatch.setattr("scripts.upstream_release._request", request)
    assert _read_url("https://api.github.com/x") == b"{}"
    assert attempts == 2


@pytest.mark.unit
@pytest.mark.parametrize(
    "error",
    [
        http.client.RemoteDisconnected("connection closed before response"),
        http.client.IncompleteRead(b"partial response"),
    ],
)
def test_an_http_client_transport_error_is_retried(
    monkeypatch: pytest.MonkeyPatch,
    no_token: None,
    instant_backoff: None,
    error: Exception,
) -> None:
    """urllib can expose response connection failures without wrapping them."""
    attempts = 0

    def request(url: str, token: str | None) -> bytes:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise error
        return b"{}"

    monkeypatch.setattr("scripts.upstream_release._request", request)
    assert _read_url("https://api.github.com/x") == b"{}"
    assert attempts == 2


@pytest.mark.unit
def test_retries_are_bounded(
    monkeypatch: pytest.MonkeyPatch, no_token: None, instant_backoff: None
) -> None:
    """A release API that stays down fails the run rather than looping."""
    attempts = 0

    def request(url: str, token: str | None) -> bytes:
        nonlocal attempts
        attempts += 1
        raise _http_error(503)

    monkeypatch.setattr("scripts.upstream_release._request", request)
    with pytest.raises(urllib.error.HTTPError):
        _read_url("https://api.github.com/x")
    assert attempts == RETRY_ATTEMPTS


@pytest.mark.unit
def test_an_incomplete_response_fails_cleanly_after_retries(
    monkeypatch: pytest.MonkeyPatch,
    no_token: None,
    instant_backoff: None,
    capsys: pytest.CaptureFixture,
) -> None:
    """An exhausted partial response is a normal CLI failure, not a traceback."""
    attempts = 0

    def request(url: str, token: str | None) -> bytes:
        nonlocal attempts
        attempts += 1
        raise http.client.IncompleteRead(b"partial response")

    monkeypatch.setattr("scripts.upstream_release._request", request)
    assert main(["resolve-tag"]) == 1
    assert attempts == RETRY_ATTEMPTS
    assert "IncompleteRead" in capsys.readouterr().err


@pytest.mark.unit
@pytest.mark.parametrize("code", [404, 403])
def test_an_answer_is_not_retried(
    monkeypatch: pytest.MonkeyPatch, no_token: None, instant_backoff: None, code: int
) -> None:
    """A missing tag and a rate limit are answers; retrying only delays the report."""
    attempts = 0

    def request(url: str, token: str | None) -> bytes:
        nonlocal attempts
        attempts += 1
        raise _http_error(code)

    monkeypatch.setattr("scripts.upstream_release._request", request)
    with pytest.raises(urllib.error.HTTPError):
        _read_url("https://api.github.com/x")
    assert attempts == 1
