"""Refuse to publish ``timezonefinder`` before the data it requires exists on PyPI.

The two distributions are released independently, and on a data format change they
have to go out in a fixed order: the data first, then the code that requires it. Get
it backwards and the code wheel is uninstallable for everyone until the data lands -
and the mistake cannot be taken back, because PyPI never accepts a version number
twice. The recovery is a new release of the code, so this has to run before anything
irreversible: build.yml calls it in the `release` job, ahead of the GitHub Release that
job publishes and creates the tag for, which is earlier than the PyPI upload in the job
downstream of it.

The requirement is read out of the **built wheel**, not out of ``pyproject.toml``: the
wheel is what gets published, and it is what a user's resolver will read. The check
then asks the index the same question that resolver will ask - is there a released,
non-yanked version satisfying this? - rather than reimplementing an answer.
"""

from argparse import ArgumentParser
import json
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import zipfile

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import InvalidVersion, Version

from scripts.configs import DATA_DISTRIBUTION_NAME

PYPI_JSON_URL = "https://pypi.org/pypi/{name}/json"
# distinguishes "nothing satisfies the requirement" from "the check could not run"
EXIT_INCOMPATIBLE = 1
EXIT_UNDETERMINED = 2


class UndeterminedError(RuntimeError):
    """The check could not be carried out, which is not the same as failing it."""


def read_requirement(wheel: Path, distribution: str) -> Requirement:
    """The wheel's declared requirement on ``distribution``.

    :raises UndeterminedError: if the wheel declares no such requirement, which would
        make every check below vacuously pass.
    """
    with zipfile.ZipFile(wheel) as archive:
        metadata_names = [
            name
            for name in archive.namelist()
            if name.endswith(".dist-info/METADATA") and name.count("/") == 1
        ]
        if len(metadata_names) != 1:
            raise UndeterminedError(
                f"expected exactly one .dist-info/METADATA in {wheel.name}, "
                f"found {metadata_names}"
            )
        metadata = archive.read(metadata_names[0]).decode("utf-8")

    wanted = canonicalize_name(distribution)
    for line in metadata.splitlines():
        if not line.startswith("Requires-Dist:"):
            continue
        requirement = Requirement(line.partition(":")[2].strip())
        if canonicalize_name(requirement.name) == wanted:
            return requirement

    raise UndeterminedError(
        f"{wheel.name} declares no dependency on {distribution}. Either the split was "
        "undone, or this guard is now checking something the wheel does not require - "
        "both of which make it pass without meaning anything."
    )


def released_versions(payload: dict) -> list[Version]:
    """The versions a resolver may install, newest first.

    A release whose files are *all* yanked is excluded: pip will not select it except
    by an exact pin, so it cannot satisfy a range and must not be counted as one that
    can. A release with no files at all is likewise not installable.
    """
    versions = []
    for raw, files in payload.get("releases", {}).items():
        if not files or all(file.get("yanked", False) for file in files):
            continue
        try:
            versions.append(Version(raw))
        except InvalidVersion:  # pragma: no cover - PyPI does not serve these
            continue
    return sorted(versions, reverse=True)


def fetch_pypi_payload(distribution: str, timeout: float = 30.0) -> dict:
    """The index's record of ``distribution``.

    :raises UndeterminedError: on any answer that is not a usable record. A 404 is not
        folded in here - a project that has never been published is a real answer, and
        the most likely one this guard exists to catch.
    """
    url = PYPI_JSON_URL.format(name=distribution)
    request = Request(url, headers={"User-Agent": "timezonefinder-release-guard"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as error:
        if error.code == 404:
            return {"releases": {}}
        raise UndeterminedError(f"{url} answered HTTP {error.code}") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise UndeterminedError(f"could not read {url}: {error}") from error


def find_wheels(dist_dir: Path, distribution: str) -> list[Path]:
    """The built wheels for one version of ``distribution`` in ``dist_dir``."""
    prefix = canonicalize_name(distribution).replace("-", "_")
    wheels = sorted(dist_dir.glob(f"{prefix}-*.whl"))
    if not wheels:
        raise UndeterminedError(f"no {prefix}-*.whl found in {dist_dir}")

    versions = sorted({parse_wheel_filename(wheel.name)[1] for wheel in wheels})
    if len(versions) != 1:
        found = ", ".join(str(version) for version in versions)
        raise UndeterminedError(
            f"expected wheels for exactly one {distribution} version in {dist_dir}, "
            f"found {found}"
        )
    return wheels


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    parser.add_argument(
        "--distribution",
        default="timezonefinder",
        help="the distribution about to be published",
    )
    args = parser.parse_args(argv)

    try:
        wheel = find_wheels(args.dist_dir, args.distribution)[0]
        requirement = read_requirement(wheel, DATA_DISTRIBUTION_NAME)
        payload = fetch_pypi_payload(DATA_DISTRIBUTION_NAME)
    except UndeterminedError as error:
        print(f"cannot verify the data dependency: {error}", file=sys.stderr)
        return EXIT_UNDETERMINED

    published = released_versions(payload)
    compatible = [v for v in published if requirement.specifier.contains(v)]
    if compatible:
        print(
            f"{wheel.name} requires {requirement}; "
            f"{DATA_DISTRIBUTION_NAME} {compatible[0]} on PyPI satisfies it"
        )
        return 0

    newest = f"newest published: {published[0]}" if published else "nothing published"
    print(
        f"::error::{wheel.name} requires '{requirement}', and no released version of "
        f"{DATA_DISTRIBUTION_NAME} satisfies it ({newest}). Publishing now would put a "
        "wheel on PyPI that nobody can install, and the version number cannot be "
        f"reused. Push the matching data tag first, confirm "
        f"`pip install '{requirement}'` resolves, then re-run this release.",
        file=sys.stderr,
    )
    return EXIT_INCOMPATIBLE


if __name__ == "__main__":
    raise SystemExit(main())
