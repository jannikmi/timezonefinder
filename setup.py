from setuptools import setup
import os

# Check whether to indicate abi3 support in a wheel name
# CFFI and setuptools use their own rules to determine ABI3 support
_abi3 = bool(os.getenv("BUILD_ABI3", ""))
print("Using ABI3 wheel suffix:", _abi3)

_build_cffi = bool(os.getenv("BUILD_CFFI", ""))
print("Using CFFI to compile extension:", _build_cffi)

setup(
    cffi_modules=["timezonefinder/build.py:ffibuilder"] if _build_cffi else [],
    options={"bdist_wheel": {"py_limited_api": "cp39"} if _abi3 else {}},
)
