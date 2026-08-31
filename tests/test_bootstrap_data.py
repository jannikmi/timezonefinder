"""What `make bootstrap` has to guarantee, tested without reaching PyPI.

The two properties worth covering are the ones a "the directory exists" check cannot
express and which fail silently when they are wrong: that a second run does no work, and
that a checkout declaring a different data version than the one on disk is reported as
stale rather than accepted. The download itself is exercised against a wheel built in
the test rather than against the network - the network path is one `urlopen`, while the
digest check, the payload selection and the replace-don't-merge unpack are the parts
with something to get wrong.
"""

import hashlib
from pathlib import Path
import re
import zipfile

import pytest

from scripts import bootstrap_data
from scripts.bootstrap_data import (
    BootstrapError,
    data_dir_is_populated,
    declared_data_version,
    describe_data_state,
    extract_data,
    download_verified,
    require_bootstrapped_data,
    select_wheel,
    staged_destination,
)
from scripts.configs import DATA_PYPROJECT_FILE, PROJECT_ROOT, SOURCE_DATA_DIR
from timezonefinder.configs import DATA_VERSION_FILENAME

pytestmark = pytest.mark.unit

# Targets that read the packaged dataset and therefore have nothing to say without it.
DATA_CONSUMING_TARGETS = ("test", "testint", "testall", "reports")


def make_data_dir(root: Path, extra: dict[str, bytes] | None = None) -> Path:
    """A directory that satisfies the populated-dataset probe."""
    data_dir = root / "data"
    (data_dir / "boundaries").mkdir(parents=True)
    (data_dir / DATA_VERSION_FILENAME).write_text("2026c\n", encoding="utf-8")
    (data_dir / "shortcuts.bin").write_bytes(b"\x00")
    for name, payload in (extra or {}).items():
        target = data_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return data_dir


def make_wheel(path: Path, files: dict[str, bytes], version: str = "9.2026.1") -> Path:
    """A ``timezonefinder-data``-shaped wheel carrying ``files`` under its data dir."""
    wheel = path / f"timezonefinder_data-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("timezonefinder_data/__init__.py", "DATA_DIR = None\n")
        for name, payload in files.items():
            archive.writestr(f"timezonefinder_data/data/{name}", payload)
    return wheel


def test_the_declared_version_is_the_one_the_workspace_pins():
    """The bootstrap must fetch what the checkout says, not what a resolver picks."""
    declared = declared_data_version()
    assert f'version = "{declared}"' in DATA_PYPROJECT_FILE.read_text(encoding="utf-8")


def test_the_committed_checkout_is_reported_as_usable():
    """A checkout that still carries the binaries has no stamp and needs none."""
    assert data_dir_is_populated(SOURCE_DATA_DIR)
    assert describe_data_state(SOURCE_DATA_DIR) is None


def test_a_missing_dataset_names_the_command_that_fixes_it(tmp_path):
    reason = describe_data_state(tmp_path / "absent")
    assert reason is not None
    with pytest.raises(BootstrapError, match="make bootstrap"):
        require_bootstrapped_data(tmp_path / "absent")


def test_a_half_unpacked_dataset_is_not_accepted(tmp_path):
    """The probe has to fail on a partial unpack, not only on an empty directory."""
    data_dir = make_data_dir(tmp_path)
    (data_dir / "shortcuts.bin").unlink()
    assert not data_dir_is_populated(data_dir)


def test_a_stale_stamp_is_reported_even_though_the_data_is_there(tmp_path, monkeypatch):
    """The failure this exists to prevent: yesterday's data against today's code.

    Every file is present, so nothing downstream would notice; only the recorded
    version disagrees with the declared one.
    """
    data_dir = make_data_dir(tmp_path)
    stamp = tmp_path / "stamp"
    stamp.write_text("1.2020.1\n", encoding="utf-8")
    monkeypatch.setattr(bootstrap_data, "STAMP_FILE", stamp)

    reason = describe_data_state(data_dir)
    assert reason is not None
    assert "1.2020.1" in reason and declared_data_version() in reason


def test_a_matching_stamp_is_accepted(tmp_path, monkeypatch):
    data_dir = make_data_dir(tmp_path)
    stamp = tmp_path / "stamp"
    stamp.write_text(f"{declared_data_version()}\n", encoding="utf-8")
    monkeypatch.setattr(bootstrap_data, "STAMP_FILE", stamp)

    assert describe_data_state(data_dir) is None


def test_a_second_bootstrap_fetches_nothing(tmp_path, monkeypatch):
    """Idempotence, asserted by making a fetch impossible rather than by timing it."""
    data_dir = make_data_dir(tmp_path)
    stamp = tmp_path / "stamp"
    stamp.write_text(f"{declared_data_version()}\n", encoding="utf-8")
    monkeypatch.setattr(bootstrap_data, "STAMP_FILE", stamp)

    def explode(*args, **kwargs):  # pragma: no cover - reaching it is the failure
        raise AssertionError("an up-to-date checkout must not contact the index")

    monkeypatch.setattr(bootstrap_data, "fetch_release_files", explode)

    assert bootstrap_data.bootstrap(data_dir, quiet=True) is False


def test_a_stale_checkout_does_fetch(tmp_path, monkeypatch):
    """The counterpart: version-awareness is what makes the skip above safe."""
    data_dir = make_data_dir(tmp_path)
    stamp = tmp_path / "stamp"
    stamp.write_text("1.2020.1\n", encoding="utf-8")
    monkeypatch.setattr(bootstrap_data, "STAMP_FILE", stamp)

    wheel = make_wheel(
        tmp_path, {DATA_VERSION_FILENAME: b"2027a\n", "shortcuts.bin": b"\x01"}
    )
    monkeypatch.setattr(
        bootstrap_data,
        "fetch_release_files",
        lambda version: [
            {
                "packagetype": "bdist_wheel",
                "filename": wheel.name,
                "url": wheel.as_uri(),
                "digests": {"sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()},
            }
        ],
    )
    # the wheel above carries no boundaries/ dir, so only the swap is under test here
    monkeypatch.setattr(bootstrap_data, "data_dir_is_populated", lambda _: True)

    assert bootstrap_data.bootstrap(data_dir, quiet=True) is True
    assert (data_dir / DATA_VERSION_FILENAME).read_bytes() == b"2027a\n"
    assert stamp.read_text(encoding="utf-8").strip() == declared_data_version()


def test_a_wrong_digest_refuses_the_download(tmp_path):
    """A truncated transfer must be refused before anything is unpacked."""
    source = tmp_path / "payload.bin"
    source.write_bytes(b"the real bytes")
    target = tmp_path / "downloaded.bin"

    with pytest.raises(BootstrapError, match="truncated or the file was substituted"):
        download_verified(source.as_uri(), "0" * 64, target)


def test_a_correct_digest_is_accepted(tmp_path):
    source = tmp_path / "payload.bin"
    source.write_bytes(b"the real bytes")
    target = tmp_path / "downloaded.bin"

    download_verified(
        source.as_uri(), hashlib.sha256(source.read_bytes()).hexdigest(), target
    )
    assert target.read_bytes() == b"the real bytes"


def test_the_unpack_replaces_rather_than_merges(tmp_path):
    """A file the previous data version had must not survive into the new one.

    Merging would leave a dataset that is neither release, which the in-file format
    identifiers can only catch later and only sometimes.
    """
    data_dir = make_data_dir(tmp_path, {"boundaries/leftover.bin": b"old"})
    wheel = make_wheel(tmp_path, {DATA_VERSION_FILENAME: b"2027a\n"})

    extract_data(wheel, data_dir)

    assert (data_dir / DATA_VERSION_FILENAME).read_bytes() == b"2027a\n"
    assert not (data_dir / "boundaries" / "leftover.bin").exists()


def test_a_wheel_without_a_payload_is_refused(tmp_path):
    """The empty-wheel failure the git-ignored `data/` makes possible."""
    wheel = make_wheel(tmp_path, {})
    with pytest.raises(BootstrapError, match="carries no"):
        extract_data(wheel, tmp_path / "data")


def test_only_a_wheel_is_accepted_from_the_index():
    """A data release is wheel-only; anything else did not come from this pipeline."""
    with pytest.raises(BootstrapError, match="exactly one wheel"):
        select_wheel([{"packagetype": "sdist", "filename": "x.tar.gz"}], "2.2026.3")


@pytest.mark.parametrize("target", DATA_CONSUMING_TARGETS)
def test_every_data_consuming_target_carries_the_guard(target: str):
    """The gate is only worth having if no data-reading entry point can omit it.

    Asserted over the prerequisite list rather than over the recipe text: what must
    hold is that the check runs first, not how the target spells what it does
    afterwards.
    """
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    match = re.search(rf"^{target}:(.*)$", makefile, flags=re.MULTILINE)
    assert match is not None, f"the Makefile no longer defines a `{target}` target"
    assert "check-data" in match.group(1).split(), (
        f"`make {target}` reads the packaged dataset but does not depend on "
        "`check-data`, so a bare or stale checkout fails somewhere inside a reader "
        "instead of being told to run `make bootstrap`"
    )


def test_an_unpublished_version_says_to_release_the_data_first(monkeypatch):
    """The precondition that blocked this item: a pinned but unreleased data version."""

    def not_found(url, timeout=None):  # pragma: no cover - raising is the point
        from urllib.error import HTTPError

        raise HTTPError(url.full_url, 404, "Not Found", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(bootstrap_data, "urlopen", not_found)
    with pytest.raises(BootstrapError, match="not published on PyPI"):
        bootstrap_data.fetch_release_files("0.1970.1")


@pytest.mark.parametrize(
    "escaping",
    [
        f"{bootstrap_data.WHEEL_DATA_PREFIX}../../Makefile",
        f"{bootstrap_data.WHEEL_DATA_PREFIX}boundaries/../../../etc/passwd",
        f"{bootstrap_data.WHEEL_DATA_PREFIX}/etc/passwd",
    ],
)
def test_a_member_that_escapes_the_staging_directory_is_refused(tmp_path, escaping):
    """A zip entry names its own path, so the wheel decides where a member lands.

    The absolute case is the one that reads as safe and is not: ``staging / "/etc/x"``
    is ``/etc/x``, because joining an absolute path discards the left side.
    """
    with pytest.raises(BootstrapError, match="would unpack outside"):
        staged_destination(tmp_path / "staging", escaping)


def test_a_hostile_wheel_writes_nothing(tmp_path):
    """The refusal has to happen before any member is written, not partway through."""
    outside = tmp_path / "victim.txt"
    outside.write_text("original", encoding="utf-8")
    wheel = tmp_path / "hostile-1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"{bootstrap_data.WHEEL_DATA_PREFIX}{DATA_VERSION_FILENAME}", "2026c"
        )
        archive.writestr(f"{bootstrap_data.WHEEL_DATA_PREFIX}../victim.txt", "owned")

    data_dir = tmp_path / "data"
    with pytest.raises(BootstrapError, match="would unpack outside"):
        extract_data(wheel, data_dir)
    assert outside.read_text(encoding="utf-8") == "original"
    assert not data_dir.exists(), "a refused wheel must not leave a partial dataset"


def test_regenerated_data_is_not_reported_stale_after_the_version_bump(
    tmp_path, monkeypatch
):
    """`update_data.sh` regenerates the data and *then* bumps the declared version.

    Without a way to restate what the directory holds, that bump makes the newest data
    in the repository read as stale, and no fetch can repair it: the version the guard
    would ask PyPI for is the one this update is still preparing.
    """
    data_dir = make_data_dir(tmp_path)
    stamp = tmp_path / ".bootstrapped-data-version"
    monkeypatch.setattr(bootstrap_data, "STAMP_FILE", stamp)

    stamp.write_text("2.2026.3\n", encoding="utf-8")
    monkeypatch.setattr(bootstrap_data, "declared_data_version", lambda: "2.2026.4")

    assert "was bootstrapped from" in (describe_data_state(data_dir) or "")

    assert bootstrap_data.mark_data_current() == "2.2026.4"
    assert describe_data_state(data_dir) is None


def test_the_regeneration_path_restates_what_the_data_directory_holds():
    """The guard above is only sound if `update_data.sh` actually calls it."""
    script = (PROJECT_ROOT / "update_data.sh").read_text(encoding="utf-8")
    assert "bootstrap_data --mark-current" in script, (
        "update_data.sh bumps the data version after regenerating the binaries, so it "
        "must restate what the data directory holds or leave every guarded target "
        "refusing the data it just produced"
    )
    bump = script.index('uv version --package "$DATA_PACKAGE"')
    assert script.index("bootstrap_data --mark-current") > bump, (
        "the stamp must be rewritten after the version bump, not before it"
    )
