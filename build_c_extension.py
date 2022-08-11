import pathlib
import re

from cffi import FFI

this_dir = pathlib.Path().resolve()
h_file_name = this_dir / "cmult.h"
c_file_name = this_dir / "cmult.c"

ffibuilder = FFI()

with open(h_file_name) as h_file:
    # cffi does not like our preprocessor directives, so we remove them
    lns = h_file.read().splitlines()
    flt = filter(lambda ln: not re.match(r" *#", ln), lns)

ffibuilder.cdef("\n".join(flt))

ffibuilder.set_source(
    "cffi_example",  # name of the output C extension
    '#include "cmult.h"',
    sources=["cmult.c"],  # includes pi.c as additional sources
    libraries=["m"],
)  # on Unix, link with the math library

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
