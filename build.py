"""optionally builds inside polygon algorithm C extension

Resources:
https://github.com/FirefoxMetzger/mini-extension
https://stackoverflow.com/questions/60073711/how-to-build-c-extensions-via-poetry
https://github.com/libmbd/libmbd/blob/master/build.py
"""

import pathlib
import re
import warnings

import cffi
import cffi.setuptools_ext
import setuptools

EXTENSION_NAME = "inside_polygon_ext"
H_FILE_NAME = "inside_polygon_int.h"
C_FILE_NAME = "inside_polygon_int.c"
# stored in "timezonefinder" package folder for cleaner footprint
EXTENSION_PATH = pathlib.Path().resolve() / "timezonefinder" / "inside_poly_extension"
h_file_path = EXTENSION_PATH / H_FILE_NAME
c_file_path = EXTENSION_PATH / C_FILE_NAME

try:
    ffibuilder = cffi.FFI()
except Exception as exc:
    warnings.warn(
        f"C lang extension cannot be build, since cffi failed with this error: {exc}"
    )
    # Clang extension should be fully optional
    ffibuilder = None

if ffibuilder is not None:
    ffibuilder.set_source(
        EXTENSION_NAME,  # name of the output C extension
        f'#include "{h_file_path}"',
        sources=[str(c_file_path)],
    )

    with open(h_file_path) as h_file:
        # cffi does not like our preprocessor directives, so we remove them
        lns = h_file.read().splitlines()
        flt = filter(lambda ln: not re.match(r" *#", ln), lns)

    ffibuilder.cdef("\n".join(flt))

    # with open(c_file_path) as c_file:
    #     # cffi does not like our preprocessor directives, so we remove them
    #     c_file_content = c_file.read()


def build_c_extension():
    if ffibuilder is None:
        warnings.warn("missing ffibuilder. skipping build process")
        return

    # not required
    # ffibuilder.compile(verbose=True)

    # Note: built into "timezonefinder" package folder
    distribution = setuptools.Distribution({"package_dir": {"": "timezonefinder"}})
    cffi.setuptools_ext.cffi_modules(
        distribution, "cffi_modules", ["build.py:ffibuilder"]
    )
    cmd = distribution.cmdclass["build_ext"](distribution)
    cmd.inplace = 1
    cmd.ensure_finalized()
    try:
        cmd.run()
    except Exception as exc:
        # distutils.errors.CompileError:
        # a build failure in the extension (e.g. C compile is not installed) must not abort the build process,
        # but instead simply not install the failing extension.
        warnings.warn(
            f"C lang extension cannot be build, since cmd.run() failed with this error: {exc}"
        )


if __name__ == "__main__":
    build_c_extension()
