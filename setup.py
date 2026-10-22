import setuptools
from setuptools import setup
from setuptools.command.build_ext import build_ext
import os
import sys
import sysconfig

# Check whether to indicate stable-ABI support in a wheel name.
# BUILD_ABI3 is set for every cibuildwheel identifier. A GIL build claims abi3 from
# the lowest supported minor up. A free-threaded build can only claim abi3t, which
# CPython has from 3.15 and setuptools accepts from 84.2.0: it raises on
# `py_limited_api` for any free-threaded build short of both, so such a build stays
# version-specific. The abi3t base is 3.15 until the floor passes it, and setuptools
# tags that wheel `abi3.abi3t`, so GIL builds from 3.15 install it as well.
# tests/test_python_version_support.py holds both bases to the supported versions.
_ABI3_BASE = "cp312"
_ABI3T_BASE = "cp315"
_free_threaded = sysconfig.get_config_var("Py_GIL_DISABLED")
_setuptools_version = tuple(int(part) for part in setuptools.__version__.split(".")[:2])
_stable_abi_buildable = not _free_threaded or (
    sys.version_info >= (3, 15) and _setuptools_version >= (84, 2)
)
_abi3 = bool(os.getenv("BUILD_ABI3", "")) and _stable_abi_buildable
_limited_api = _ABI3T_BASE if _free_threaded else _ABI3_BASE
print(
    "Using stable-ABI wheel suffix:", _limited_api if _abi3 else False, file=sys.stderr
)


class fallible_build_ext(build_ext):
    def run(self):
        try:
            return build_ext.run(self)
        except Exception as e:
            print(
                f"Failed to build CFFI extension: {e}, proceed with non-native implementation",
                file=sys.stderr,
            )


setup(
    cffi_modules=["timezonefinder/build.py:ffibuilder"],
    cmdclass={"build_ext": fallible_build_ext},
    options={"bdist_wheel": {"py_limited_api": _limited_api} if _abi3 else {}},
)
