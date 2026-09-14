from setuptools import setup
from setuptools.command.build_ext import build_ext
import os
import sys
import sysconfig

# Check whether to indicate abi3 support in a wheel name.
# BUILD_ABI3 is set for every cibuildwheel identifier, but no free-threaded
# build may claim it: setuptools' bdist_wheel raises on `py_limited_api` whenever
# Py_GIL_DISABLED is set (checked in 84.0.0), 3.15t included, even though cffi
# already builds a stable-ABI module there. The stricter of the two gates wins.
_free_threaded = sysconfig.get_config_var("Py_GIL_DISABLED")
_abi3 = bool(os.getenv("BUILD_ABI3", "")) and not _free_threaded
print("Using ABI3 wheel suffix:", _abi3, file=sys.stderr)


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
    options={"bdist_wheel": {"py_limited_api": "cp312"} if _abi3 else {}},
)
