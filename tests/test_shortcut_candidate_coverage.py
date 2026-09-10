"""Exercise one-time dataset validation without repeating full audits in tox."""

import json
import os
import shutil
import subprocess
import sys

import pytest

from tests.auxiliaries import PROJECT_ROOT

pytestmark = pytest.mark.unit
MODES = ["cell-edges", "source-edges", "seams"]


@pytest.fixture
def run_data_validation(tmp_path):
    """Run the real update script with external download/conversion commands stubbed.

    The vendor command stops a successful full update at release preparation; a
    failed audit must stop earlier, including in the binaries-only path.
    """
    shutil.copy(PROJECT_ROOT / "update_data.sh", tmp_path)
    staging = tmp_path / "tmp"
    staging.mkdir()
    (staging / "data_downloaded-2026c.zip").touch()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "stub"
    stub.write_text(
        f"#!{sys.executable}\n"
        + """import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open("calls.jsonl", "a") as log:
    log.write(json.dumps([name, *args]) + "\\n")
if name == "unzip":
    pathlib.Path("tmp/combined.json").touch()
elif name == "git":
    sys.exit(1)
elif name == "uv":
    if "verify" in args:
        pathlib.Path(args[args.index("--stage") + 1]).write_text("sha256=test\\n")
    if "scripts.audit_shortcut_candidates" in args:
        mode = args[args.index("--mode") + 1]
        pathlib.Path(args[args.index("--output") + 1]).write_text("{}")
        if mode == os.environ.get("FAIL_AUDIT"):
            sys.exit(1)
    if "vendor-zone-mapping" in args:
        sys.exit(42)
""",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    for name in ("uv", "unzip", "git"):
        (bin_dir / name).symlink_to(stub)

    def run(*, failed_mode="", binaries_only=False):
        result = subprocess.run(
            ["bash", str(tmp_path / "update_data.sh"), "--tag=2026c"]
            + (["--binaries-only"] if binaries_only else []),
            env={
                **os.environ,
                "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
                "FAIL_AUDIT": failed_mode,
            },
            text=True,
            capture_output=True,
        )
        calls = [
            json.loads(line)
            for line in (tmp_path / "calls.jsonl").read_text().splitlines()
        ]
        return result, calls

    return run


@pytest.mark.parametrize("binaries_only", [False, True])
def test_dataset_validation_runs_all_streams_before_release_preparation(
    run_data_validation, binaries_only
):
    result, calls = run_data_validation(binaries_only=binaries_only)
    # The script translates the vendor sentinel's failure to 1; reaching it proves
    # all audits ran before release preparation. Binaries-only completes normally.
    assert result.returncode == (0 if binaries_only else 1), result.stderr
    audits = [c for c in calls if "scripts.audit_shortcut_candidates" in c]
    assert [c[c.index("--mode") + 1] for c in audits] == MODES
    assert all("--max-points" not in c and "--points" not in c for c in audits)
    converter = next(c for c in calls if "scripts.file_converter" in c)
    assert calls.index(converter) < calls.index(audits[0])
    if not binaries_only:
        vendor = next(c for c in calls if "vendor-zone-mapping" in c)
        assert calls.index(audits[-1]) < calls.index(vendor)


@pytest.mark.parametrize("binaries_only", [False, True])
@pytest.mark.parametrize("failed_mode", MODES)
def test_candidate_omission_stops_dataset_preparation(
    run_data_validation, failed_mode, binaries_only, tmp_path
):
    result, calls = run_data_validation(
        failed_mode=failed_mode, binaries_only=binaries_only
    )
    assert result.returncode == 1
    assert "shortcut candidate validation failed" in result.stderr
    audits = [c for c in calls if "scripts.audit_shortcut_candidates" in c]
    assert [c[c.index("--mode") + 1] for c in audits] == MODES[
        : MODES.index(failed_mode) + 1
    ]
    assert not (tmp_path / "DATA_VERSION").exists()
    assert not any("vendor-zone-mapping" in c for c in calls)
    assert (tmp_path / "tmp" / f"shortcut-candidates-{failed_mode}.json").exists()
