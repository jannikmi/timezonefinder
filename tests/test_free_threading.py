"""What a free-threaded interpreter does with this package.

Skipped everywhere else. The `free-threaded` tox env runs it, and `build.yml`
invokes that env, so this is the one check in the repository that can say whether
the GIL stays disabled.
"""

import os
import subprocess
import sys
import sysconfig

import pytest

FREE_THREADED = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))


@pytest.mark.unit
@pytest.mark.skipif(not FREE_THREADED, reason="needs a free-threaded interpreter")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "h3 4.5.0 ships without Py_mod_gil, so loading it re-enables the GIL. "
        "Strict so the h3 release that fixes it fails here: raise the h3 floor "
        "and drop this xfail together."
    ),
)
def test_using_a_finder_keeps_the_gil_disabled():
    # In a fresh interpreter: the GIL never turns back off within a process, so
    # in-process this would read whatever the session loaded first rather than
    # this package. PYTHON_GIL is dropped because it would force either answer.
    # `raises=AssertionError`: a subprocess that fails to run must fail the test,
    # not satisfy the expected failure.
    # Not `import timezonefinder` alone: that does not load h3, while importing
    # the `TimezoneFinder` class does.
    env = {k: v for k, v in os.environ.items() if k != "PYTHON_GIL"}
    code = (
        "import sys\n"
        "from timezonefinder import TimezoneFinder\n"
        "TimezoneFinder().timezone_at(lng=13.4, lat=52.5)\n"
        "print(sys._is_gil_enabled())\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert result.stdout.strip() == "False"
