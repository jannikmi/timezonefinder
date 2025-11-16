from setuptools import setup
from setuptools.command.build_ext import build_ext
import os
import sys

# Check whether to indicate abi3 support in a wheel name
# CFFI and setuptools use their own rules to determine ABI3 support
_abi3 = bool(os.getenv("BUILD_ABI3", ""))
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
    options={"bdist_wheel": {"py_limited_api": "cp39"} if _abi3 else {}},
)
