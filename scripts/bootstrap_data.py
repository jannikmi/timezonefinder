"""Populate the checkout's packaged boundary data from the published data wheel.

``packages/timezonefinder-data/timezonefinder_data/data/`` is where the converter
writes and where an editable install reads from, and it is the ~62 MB that makes every
regeneration expensive to keep in this repository's history (DATA-BINARIES). This
module is the *consuming* half of stopping that: a checkout that does not carry the
binaries obtains them here instead, from the ``timezonefinder-data`` release the
workspace already pins.

Two properties the directory cannot supply on its own, and which the entry points below
depend on:

**Idempotent.** A second run does no work. What makes that safe is the stamp file
beside the data directory rather than inside it - ``data/`` is package data, so a marker
in there would be published in the next wheel and would then describe the machine that
built it.

**Version-aware.** The stamp records *which* ``timezonefinder-data`` version the data
directory holds. A checkout that moves to a commit declaring a different one is stale,
not merely populated, and ``--check`` says so: the failure mode this exists to prevent
is a run that silently tests yesterday's data against today's code, which no amount of
"the directory is there" can detect.

The stamp says what the directory *holds*, not where it came from, because the data has
a second producer: ``update_data.sh`` regenerates it from upstream and then bumps the
declared version. That output is the newest data there is and is not yet published
anywhere, so ``--mark-current`` is how the regeneration states it - without it the bump
would make the freshly generated dataset read as stale, and no fetch could repair it.

The wheel is fetched from PyPI and its SHA-256 is checked against the digest the index
publishes for it, so a truncated or substituted download is refused before anything is
unpacked. Only ``timezonefinder_data/data/**`` is extracted; the wheel's Python module
is already in the checkout.
"""

from argparse import ArgumentParser
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import tomllib
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import zipfile

from scripts.configs import (
    DATA_DISTRIBUTION_NAME,
    DATA_PACKAGE_ROOT,
    DATA_PYPROJECT_FILE,
    SOURCE_DATA_DIR,
)
from timezonefinder.configs import DATA_VERSION_FILENAME
from timezonefinder.shortcut_index import get_shortcut_file_path
from timezonefinder.utils import get_boundaries_dir

PYPI_RELEASE_URL = "https://pypi.org/pypi/{name}/{version}/json"

# Beside the data directory, never inside it: `data/` is what the wheel ships, and a
# marker in there would travel to PyPI with the next data release.
STAMP_FILE = DATA_PACKAGE_ROOT / ".bootstrapped-data-version"

# The prefix inside the wheel. `packages = ["timezonefinder_data"]` in the data
# package's pyproject is what puts the payload here.
WHEEL_DATA_PREFIX = "timezonefinder_data/data/"

# One wording, so every entry point that refuses to run without the data names the same
# command. Deliberately path-free: the caller's own reason already says which directory.
BOOTSTRAP_HINT = (
    "Run `make bootstrap` to fetch the packaged boundary data from the published "
    f"{DATA_DISTRIBUTION_NAME} wheel."
)


class BootstrapError(RuntimeError):
    """The data could not be obtained, or what is on disk is not what is declared."""


def declared_data_version() -> str:
    """The ``timezonefinder-data`` version this checkout pins."""
    with DATA_PYPROJECT_FILE.open("rb") as file:
        return str(tomllib.load(file)["project"]["version"])


def stamped_data_version() -> str | None:
    """The version a previous bootstrap unpacked, or ``None`` if never bootstrapped.

    ``None`` is not "broken": a checkout that still carries the binaries in git has no
    stamp and needs none.
    """
    if not STAMP_FILE.is_file():
        return None
    return STAMP_FILE.read_text(encoding="utf-8").strip() or None


def mark_data_current() -> str:
    """Record that the data directory holds the version this checkout declares.

    For the *other* producer of that directory: ``update_data.sh`` regenerates the
    binaries from upstream and then bumps the data package's version, which leaves a
    stamp from before the bump describing data that no longer exists. Everything
    guarded by ``--check`` - ``make test``, ``make testall``, ``make reports`` - would
    then refuse the newest data in the repository, and ``bootstrap`` could not fix it:
    the version it would fetch is the one the update is *preparing* and PyPI does not
    have it yet. Returns the version stamped, so the caller can echo it.
    """
    version = declared_data_version()
    STAMP_FILE.write_text(f"{version}\n", encoding="utf-8")
    return version


def data_dir_is_populated(data_dir: Path = SOURCE_DATA_DIR) -> bool:
    """Whether ``data_dir`` holds a dataset rather than nothing or a partial unpack."""
    return (
        (data_dir / DATA_VERSION_FILENAME).is_file()
        and get_shortcut_file_path(data_dir).is_file()
        and get_boundaries_dir(data_dir).is_dir()
    )


def describe_data_state(data_dir: Path = SOURCE_DATA_DIR) -> str | None:
    """``None`` when the data is usable, otherwise why it is not.

    Split from the raising helper below so ``--check`` can print the reason without
    catching an exception it would only re-raise.
    """
    if not data_dir_is_populated(data_dir):
        return f"no dataset found at {data_dir}"
    stamped = stamped_data_version()
    declared = declared_data_version()
    if stamped is not None and stamped != declared:
        return (
            f"the dataset at {data_dir} was bootstrapped from "
            f"{DATA_DISTRIBUTION_NAME} {stamped}, but this checkout declares {declared}"
        )
    return None


def require_bootstrapped_data(data_dir: Path = SOURCE_DATA_DIR) -> None:
    """Fail early, and by name, instead of somewhere inside a reader.

    :raises BootstrapError: with the command that fixes it.
    """
    reason = describe_data_state(data_dir)
    if reason is not None:
        raise BootstrapError(f"{reason}. {BOOTSTRAP_HINT}")


def fetch_release_files(version: str, timeout: float = 30.0) -> list[dict]:
    """The index's file records for one released ``timezonefinder-data`` version."""
    url = PYPI_RELEASE_URL.format(name=DATA_DISTRIBUTION_NAME, version=version)
    request = Request(url, headers={"User-Agent": "timezonefinder-bootstrap"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as error:
        if error.code == 404:
            raise BootstrapError(
                f"{DATA_DISTRIBUTION_NAME} {version} is not published on PyPI. A "
                "checkout pinning an unreleased data version cannot bootstrap; publish "
                "the data release first (see contributing/development/"
                "data-pipeline-format-versioning-and-release-order.md)."
            ) from error
        raise BootstrapError(f"{url} answered HTTP {error.code}") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise BootstrapError(f"could not read {url}: {error}") from error
    return list(payload.get("urls", []))


def select_wheel(files: list[dict], version: str) -> dict:
    """The one wheel a data release publishes.

    A data release is wheel-only on purpose (there is no build-from-source case for a
    pure-data ``py3-none-any`` distribution), so anything else here means the release
    was not built by this repository's pipeline.
    """
    wheels = [file for file in files if file.get("packagetype") == "bdist_wheel"]
    if len(wheels) != 1:
        names = (
            ", ".join(sorted(file.get("filename", "?") for file in wheels)) or "none"
        )
        raise BootstrapError(
            f"expected exactly one wheel for {DATA_DISTRIBUTION_NAME} {version}, "
            f"found: {names}"
        )
    return wheels[0]


def download_verified(url: str, expected_sha256: str, target: Path) -> None:
    """Download ``url`` to ``target``, refusing bytes that do not hash as promised.

    :raises BootstrapError: on a transport failure or a digest mismatch. The digest is
        the index's own statement about the file, so this catches a truncated transfer
        as well as a substituted one - a partial wheel would otherwise unpack into a
        dataset that is merely incomplete, which is far harder to diagnose.
    """
    digest = hashlib.sha256()
    request = Request(url, headers={"User-Agent": "timezonefinder-bootstrap"})
    try:
        with urlopen(request, timeout=120.0) as response, target.open("wb") as file:
            while chunk := response.read(1 << 20):
                digest.update(chunk)
                file.write(chunk)
    except (HTTPError, URLError, TimeoutError) as error:
        raise BootstrapError(f"could not download {url}: {error}") from error

    actual = digest.hexdigest()
    if actual != expected_sha256:
        raise BootstrapError(
            f"{url} hashed to {actual}, but the index publishes {expected_sha256}. "
            "The download is truncated or the file was substituted; nothing was "
            "unpacked."
        )


def staged_destination(staging: Path, member: str) -> Path:
    """Where ``member`` unpacks to, refusing any name that escapes ``staging``.

    A zip entry carries its own path, so a crafted or malformed wheel can name
    ``timezonefinder_data/data/../../Makefile`` - or a suffix starting with ``/``, which
    ``Path.__truediv__`` resolves to the absolute path rather than below ``staging`` -
    and write wherever the developer running ``make bootstrap`` can write. The index
    digest checked before this does not cover it: it certifies that these are the bytes
    PyPI published, not that they are benign, so a malicious release carries a matching
    digest for its own payload.

    The check is on the name rather than on a resolved path because the unpack writes
    file bytes and never creates a symlink, so there is no link for a later member to
    be redirected through.

    :raises BootstrapError: naming the member, since a wheel that trips this is a
        supply-chain event and not a transient failure to retry.
    """
    relative = Path(member[len(WHEEL_DATA_PREFIX) :])
    if relative.is_absolute() or ".." in relative.parts:
        raise BootstrapError(
            f"{member!r} would unpack outside {staging}. The wheel is malformed or "
            "hostile; nothing was written."
        )
    return staging / relative


def extract_data(wheel: Path, data_dir: Path) -> int:
    """Replace ``data_dir`` with the wheel's payload. Returns the file count.

    The directory is rebuilt rather than merged: a file the previous data version had
    and this one does not would otherwise survive, and a mixed dataset is exactly what
    the in-file format identifiers exist to catch late instead of never.
    """
    with zipfile.ZipFile(wheel) as archive:
        members = [
            name
            for name in archive.namelist()
            if name.startswith(WHEEL_DATA_PREFIX) and not name.endswith("/")
        ]
        if not members:
            raise BootstrapError(
                f"{wheel.name} carries no {WHEEL_DATA_PREFIX} payload. It was built "
                "from a tree whose data directory was empty."
            )
        staging = data_dir.parent / f".{data_dir.name}.incoming"
        shutil.rmtree(staging, ignore_errors=True)
        try:
            for name in members:
                destination = staged_destination(staging, name)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as source, destination.open("wb") as file:
                    shutil.copyfileobj(source, file)
            # Swap last: an interrupted unpack must not leave a half-populated
            # directory that `data_dir_is_populated` would then accept.
            shutil.rmtree(data_dir, ignore_errors=True)
            staging.replace(data_dir)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    return len(members)


def bootstrap(
    data_dir: Path = SOURCE_DATA_DIR, force: bool = False, quiet: bool = False
) -> bool:
    """Ensure ``data_dir`` holds the declared data version. Returns whether it fetched.

    :raises BootstrapError: if the declared version cannot be obtained.
    """

    def say(message: str) -> None:
        if not quiet:
            print(message)

    version = declared_data_version()
    if not force and describe_data_state(data_dir) is None:
        say(f"{DATA_DISTRIBUTION_NAME} {version} data already present at {data_dir}")
        return False

    say(f"fetching {DATA_DISTRIBUTION_NAME} {version} from PyPI...")
    wheel_record = select_wheel(fetch_release_files(version), version)
    with tempfile.TemporaryDirectory() as scratch:
        wheel = Path(scratch) / str(wheel_record["filename"])
        download_verified(
            str(wheel_record["url"]),
            str(wheel_record["digests"]["sha256"]),
            wheel,
        )
        count = extract_data(wheel, data_dir)
    mark_data_current()
    say(f"unpacked {count} files into {data_dir} ({DATA_DISTRIBUTION_NAME} {version})")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report whether the data is present and current; fetch nothing",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-fetch even when the declared version is already unpacked",
    )
    parser.add_argument(
        "--mark-current",
        action="store_true",
        help=(
            "record the declared version as what the data directory holds, without "
            "fetching; for the regeneration path, which produces data no release has"
        ),
    )
    parser.add_argument("--data-dir", type=Path, default=SOURCE_DATA_DIR)
    args = parser.parse_args(argv)

    if args.mark_current:
        print(
            f"stamped the data directory as {DATA_DISTRIBUTION_NAME} {mark_data_current()}"
        )
        return 0

    if args.check:
        reason = describe_data_state(args.data_dir)
        if reason is None:
            print(f"boundary data present at {args.data_dir}")
            return 0
        print(f"::error::{reason}. {BOOTSTRAP_HINT}", file=sys.stderr)
        return 1

    try:
        bootstrap(args.data_dir, force=args.force)
    except BootstrapError as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
