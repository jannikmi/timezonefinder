"""The upstream release ``update_data.sh`` downloads, resolved and verified.

The data update pipeline is unattended end to end: a weekly job runs
``update_data.sh``, and ``release_data_update.yml`` merges the pull request it opens
and pushes the tag that publishes to PyPI. Until this module nothing in that chain
ever looked at the ~55 MB archive it had downloaded, so a truncated transfer, a
half-written leftover in ``tmp/`` or an asset replaced upstream reached the converter
as ordinary input and was compiled into a release.

timezone-boundary-builder publishes no checksum file, but the GitHub release API
states a SHA-256 ``digest`` and a byte ``size`` for every asset. That is the
independent statement of what the bytes should be - independent of the transfer that
fetched them, which is the whole point - and this module is the only thing that reads
it. Verification is therefore possible without asking upstream for anything new.

The verified digest is then staged, for the caller to install as ``DATA_SOURCE``
beside ``DATA_VERSION`` once the parse has succeeded - the same two-step
``update_data.sh`` already uses for the release tag, and for the same reason: a run
that fails between verifying and parsing must not leave the two stamps naming
different releases. The record states in an update pull request which upstream bytes
produced its binaries, and lets a later run notice an asset that was replaced in
place - the one corruption the API digest cannot report, since it moves with the
asset.
"""

import hashlib
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.configs import DATA_SOURCE_FILE, DATA_VERSION_TAG_PATTERN

RELEASES_API = (
    "https://api.github.com/repos/evansiroky/timezone-boundary-builder/releases"
)

# The only digest algorithm the API is asked for. GitHub currently publishes SHA-256
# and nothing else; an asset announcing anything different is refused rather than
# trusted, since a weaker digest verified as if it were this one asserts less than the
# message would claim.
DIGEST_PREFIX = "sha256:"

# Read in blocks rather than whole: the archives are ~55 MB and the runner hashing
# them is the same one holding the parsed GeoJSON later in the run.
HASH_CHUNK_BYTES = 1 << 20

# ``DATA_SOURCE``'s fields, in the order it is written. Parsing is order-independent;
# only the rendering is fixed, so that a re-record produces a one-line diff per field
# that actually moved.
RECORD_FIELDS = ("tag", "asset", "size", "sha256")

_TIMEOUT_SECONDS = 60

# Checked in order, first non-empty wins. Both are conventional names for a
# GitHub credential, and CI sets the first one on the job that runs update_data.sh.
TOKEN_VARIABLES = ("GH_TOKEN", "GITHUB_TOKEN")

# Matching the `curl --retry 3` this module replaced. The weekly update is unattended
# and a failure here opens a maintenance issue for a human, so a blip that resolves
# itself in a second must not cost that: the release API is read twice per run and
# neither read is idempotency-sensitive.
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2.0

# urllib wraps many transport failures in URLError, but exceptions raised while
# reading the HTTP response can escape directly from http.client instead.
TRANSIENT_TRANSPORT_ERRORS = (
    urllib.error.URLError,
    TimeoutError,
    http.client.RemoteDisconnected,
    http.client.IncompleteRead,
)


@dataclass(frozen=True)
class UpstreamAsset:
    """One release asset, as upstream describes it or as ``DATA_SOURCE`` records it."""

    tag: str
    asset: str
    size: int
    sha256: str

    def render(self) -> str:
        """The ``DATA_SOURCE`` text for this asset."""
        values = {
            "tag": self.tag,
            "asset": self.asset,
            "size": str(self.size),
            "sha256": self.sha256,
        }
        return "".join(f"{field}: {values[field]}\n" for field in RECORD_FIELDS)

    @classmethod
    def parse(cls, text: str) -> "UpstreamAsset":
        """Read back what :meth:`render` wrote.

        :raises ValueError: if a field is missing, repeated, unknown or unparsable.
            The file is written by ``update_data.sh`` and read by the verification
            that guards the next update, so a record nobody can parse has to be an
            error rather than a silently skipped comparison.
        """
        values: dict[str, str] = {}
        for number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            field, separator, value = line.partition(":")
            if not separator:
                raise ValueError(f"line {number} is not '<field>: <value>': {line!r}")
            field, value = field.strip(), value.strip()
            if field not in RECORD_FIELDS:
                raise ValueError(f"line {number} names an unknown field {field!r}")
            if field in values:
                raise ValueError(f"line {number} repeats the field {field!r}")
            values[field] = value

        missing = [field for field in RECORD_FIELDS if field not in values]
        if missing:
            raise ValueError(f"missing field(s): {', '.join(missing)}")
        if not values["size"].isdigit():
            raise ValueError(f"size is not a byte count: {values['size']!r}")
        return cls(
            tag=values["tag"],
            asset=values["asset"],
            size=int(values["size"]),
            sha256=values["sha256"],
        )


def _request(url: str, token: str | None) -> bytes:
    """Fetch ``url``, presenting ``token`` when there is one.

    The single network boundary of this module, so that everything above it is
    exercised offline.
    """
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "timezonefinder-update-data",
        },
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
        data: bytes = response.read()
    return data


def _is_transient(error: Exception) -> bool:
    """Whether retrying ``error`` could plausibly succeed.

    ``HTTPError`` is checked first because it *is* a ``URLError``: a 404 for a tag
    that does not exist, or a 401 for a bad credential, is an answer rather than a
    blip, and retrying it only delays the report. What is worth another attempt is a
    server-side failure, the documented secondary-rate-limit 429, and the transport
    errors that carry no status at all - a reset connection, a DNS hiccup, a timeout.
    """
    if isinstance(error, urllib.error.HTTPError):
        return error.code == 429 or error.code >= 500
    return isinstance(error, TRANSIENT_TRANSPORT_ERRORS)


def _sleep(seconds: float) -> None:
    """Indirection so the retry tests do not spend the backoff."""
    time.sleep(seconds)


def _fetch(url: str, token: str | None) -> bytes:
    """``_request`` with bounded retries over transient failures."""
    attempt = 1
    while True:
        try:
            return _request(url, token)
        except TRANSIENT_TRANSPORT_ERRORS as error:
            if attempt >= RETRY_ATTEMPTS or not _is_transient(error):
                raise
            print(
                f"{url} failed with {error} (attempt {attempt} of "
                f"{RETRY_ATTEMPTS}); retrying",
                file=sys.stderr,
            )
            _sleep(RETRY_BACKOFF_SECONDS * attempt)
            attempt += 1


def _read_url(url: str) -> bytes:
    """Fetch ``url``, using an environment token only while it is being accepted.

    Authentication is optional here and buys nothing but API quota: the release data
    is public, and a runner making two unauthenticated calls per update shares its
    rate limit with every other caller on its address. So a *rejected* credential is
    the environment's problem rather than the request's - a token left over in a
    developer's shell must not be able to fail a request that needs no token at all,
    which is what happens when it has expired or been revoked.

    Only 401 falls back. A 403 with a token is usually the rate limit, and retrying
    that unauthenticated would trade a good diagnosis for a worse one against a
    stricter limit.
    """
    variable = next(
        (name for name in TOKEN_VARIABLES if os.environ.get(name)),
        None,
    )
    if variable is None:
        return _fetch(url, None)
    try:
        return _fetch(url, os.environ[variable])
    except urllib.error.HTTPError as error:
        if error.code != 401:
            raise
        print(
            f"{variable} was rejected by {url} ({error.code} {error.reason}); "
            "the release API is public, so retrying without it",
            file=sys.stderr,
        )
        return _fetch(url, None)


def fetch_release(tag: str | None = None) -> dict[str, Any]:
    """The release API's description of ``tag``, or of the latest release.

    :raises ValueError: if the response is not a JSON object.
    """
    url = f"{RELEASES_API}/tags/{tag}" if tag else f"{RELEASES_API}/latest"
    payload = json.loads(_read_url(url))
    if not isinstance(payload, dict):
        raise ValueError(f"{url} did not describe a release: {payload!r}")
    return payload


def release_tag(release: dict[str, Any]) -> str:
    """The validated release tag of a release description.

    :raises ValueError: if the tag is absent or not a timezone-boundary-builder tag.
        Everything downstream is named after it - the download URL, the input file,
        ``DATA_VERSION`` and the data distribution's version - so a tag that is not
        one stops the run here rather than at the four places that would inherit it.
    """
    tag = release.get("tag_name")
    if not isinstance(tag, str) or not DATA_VERSION_TAG_PATTERN.fullmatch(tag):
        raise ValueError(
            f"unexpected release tag from the GitHub API: {tag!r}. A "
            "timezone-boundary-builder release is four digits and one or more "
            "lowercase letters, e.g. '2026c'"
        )
    return tag


def published_asset(release: dict[str, Any], asset_name: str) -> UpstreamAsset:
    """What upstream says the asset named ``asset_name`` should be.

    :raises ValueError: if the release has no such asset, or the asset publishes no
        usable SHA-256. An asset with no digest is refused rather than downloaded
        unverified: an unattended pipeline that publishes whatever it fetched is
        exactly what this guard exists to prevent, and the failure path - a
        maintainer running ``update_data.sh`` by hand - already exists.
    """
    tag = release_tag(release)
    assets = release.get("assets") or []
    for asset in assets:
        if asset.get("name") != asset_name:
            continue
        digest = asset.get("digest")
        if not isinstance(digest, str) or not digest.startswith(DIGEST_PREFIX):
            raise ValueError(
                f"release {tag} publishes no {DIGEST_PREFIX.rstrip(':')} digest for "
                f"{asset_name!r} (got {digest!r}), so the download cannot be "
                "verified. Check the asset by hand before parsing it."
            )
        size = asset.get("size")
        if not isinstance(size, int):
            raise ValueError(
                f"release {tag} states no byte size for {asset_name!r}: {size!r}"
            )
        return UpstreamAsset(
            tag=tag,
            asset=asset_name,
            size=size,
            sha256=digest[len(DIGEST_PREFIX) :],
        )

    listed = ", ".join(sorted(str(asset.get("name")) for asset in assets)) or "nothing"
    raise ValueError(
        f"release {tag} has no asset named {asset_name!r}; it publishes {listed}"
    )


def sha256_of(path: Path) -> str:
    """The SHA-256 of a file on disk, read in blocks."""
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        while chunk := file.read(HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def verify_archive(archive: Path, published: UpstreamAsset) -> None:
    """Check the bytes on disk against what upstream published.

    The size is compared first and reported on its own, because a truncated or
    interrupted transfer is the failure this is most likely to meet and its byte
    count says so directly - where a digest mismatch alone would not distinguish it
    from a replaced asset.

    :raises ValueError: on any disagreement.
    """
    actual_size = archive.stat().st_size
    if actual_size != published.size:
        raise ValueError(
            f"{archive} is {actual_size} bytes, but release {published.tag} "
            f"publishes {published.asset} as {published.size} bytes. The download is "
            "incomplete or is not that asset; delete it and run this again."
        )
    actual_sha256 = sha256_of(archive)
    if actual_sha256 != published.sha256:
        raise ValueError(
            f"{archive} hashes to {actual_sha256}, but release {published.tag} "
            f"publishes {published.asset} as {published.sha256}. The bytes are not "
            "the ones upstream released; nothing is parsed from them."
        )


def check_against_record(
    record: UpstreamAsset | None, published: UpstreamAsset
) -> None:
    """Refuse an asset upstream replaced under a tag this repository already used.

    The API digest travels with the asset, so it agrees with itself after a
    re-upload and cannot report one. ``DATA_SOURCE`` is the only statement of what
    the tag held when its data was built, which is what makes this comparison
    possible at all.

    :raises ValueError: if the recorded asset and the published one disagree.
    """
    if record is None or record.tag != published.tag or record.asset != published.asset:
        return
    if record == published:
        return
    raise ValueError(
        f"release {published.tag} now publishes {published.asset} as "
        f"{published.size} bytes / {published.sha256}, but {DATA_SOURCE_FILE.name} "
        f"records {record.size} bytes / {record.sha256} for the same asset. Upstream "
        "replaced a released asset in place; the packaged data was built from the "
        "recorded one. Resolve this by hand before parsing anything."
    )


def read_record(path: Path) -> UpstreamAsset | None:
    """The recorded upstream asset, or ``None`` when nothing is recorded yet."""
    if not path.is_file():
        return None
    return UpstreamAsset.parse(path.read_text(encoding="utf-8"))


def write_record(path: Path, asset: UpstreamAsset) -> None:
    """Write the verified ``asset`` out, for the caller to install after the parse."""
    path.write_text(asset.render(), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Resolve or verify the upstream release, for ``update_data.sh``."""
    parser = ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    # the shell names its download, its unpacked input and DATA_VERSION after this,
    # so it has to have the tag before it can fetch anything
    subparsers.add_parser("resolve-tag")

    verify_parser = subparsers.add_parser("verify")
    # by tag, never "latest": the shell resolved the tag before downloading, and a
    # release landing in between must not make this describe a different one
    verify_parser.add_argument("--tag", required=True)
    verify_parser.add_argument("--asset", required=True)
    verify_parser.add_argument("--archive", type=Path, required=True)
    # what the packaged data was built from, read to catch an asset replaced in place
    verify_parser.add_argument("--record", type=Path, default=DATA_SOURCE_FILE)
    # Where to leave the verified record, and deliberately not --record's file: the
    # caller stages it and installs it beside DATA_VERSION only once the parse has
    # succeeded, so that a run failing in between cannot leave the two stamps naming
    # different releases. Omitted, this verifies and writes nothing.
    verify_parser.add_argument("--stage", type=Path, default=None)

    args = parser.parse_args(argv)
    try:
        if args.command == "resolve-tag":
            print(release_tag(fetch_release()))
            return 0

        published = published_asset(fetch_release(args.tag), args.asset)
        check_against_record(read_record(args.record), published)
        verify_archive(args.archive, published)
        if args.stage is not None:
            write_record(args.stage, published)
        print(
            f"verified {args.archive} against {args.tag}/{args.asset} "
            f"({published.size} bytes, sha256 {published.sha256})"
        )
        return 0
    except (OSError, ValueError, *TRANSIENT_TRANSPORT_ERRORS) as error:
        print(f"{parser.prog}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
