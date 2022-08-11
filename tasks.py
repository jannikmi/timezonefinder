""" Task definitions for invoke command line utility for python bindings
    overview article.
"""
import glob
import os
import pathlib
import shutil
import sys

import cffi
import invoke

on_win = sys.platform.startswith("win")
ffi = cffi.FFI()

this_dir = pathlib.Path().resolve()
h_file_name = this_dir / "cmult.h"
c_file_name = this_dir / "cmult.c"


@invoke.task
def clean(c):
    """Remove any built objects"""
    for file_pattern in (
        "*.o",
        "*.so",
        "*.obj",
        "*.dll",
        "*.exp",
        "*.lib",
        "*.pyd",
        "cffi_example*",  # Is this a dir?
        "cython_wrapper.cpp",
    ):
        for file in glob.glob(file_pattern):
            os.remove(file)
    for dir_pattern in "Release":
        for dir in glob.glob(dir_pattern):
            shutil.rmtree(dir)


def print_banner(msg):
    print("==================================================")
    print("= {} ".format(msg))


@invoke.task()
def build_cffi(c):
    """Build the CFFI Python bindings"""
    print_banner("Building CFFI Module")
    invoke.run("python build_c_extension.py")
    print("* Complete")


@invoke.task()
def test_cffi(c):
    """Run the script to test CFFI"""
    print_banner("Testing CFFI Module")

    invoke.run("python build_c_extension.py")

    print("running unit test")
    invoke.run("pytest tests/utils_test.py::test_inside_polygon -s")
    #
    # # IDE might complain with "no module found" here, even when it exists
    # import cffi_example
    #
    # # numpy.ascontiguousarray before passing it to the buffer if there is a chance the array
    # does not have a C_CONTIGUOUS memory layout.
    # # https://numpy.org/doc/stable/reference/generated/
    # numpy.ascontiguousarray.html?highlight=ascontiguousarray#numpy.ascontiguousarray
    # x_coords = np.ascontiguousarray([0, 1, 2])#, dtype=np.int)
    # y_coords = np.ascontiguousarray([0, 1, 2])#, dtype=np.int)
    # x_coords_ffi = ffi.from_buffer("int []", x_coords)
    # y_coords_ffi = ffi.from_buffer("int []", y_coords)
    #
    # answer = cffi_example.lib.cmult(1, 2, len(x_coords), x_coords_ffi,y_coords_ffi)
    # print(f"    In Python: return val {answer}")
