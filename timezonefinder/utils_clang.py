from typing import Final

import cffi

import numpy as np

ffi: cffi.FFI | None = None
try:
    # Note: IDE might complain as this import comes from a cffi C extension
    from timezonefinder import inside_polygon_ext  # type: ignore

    clang_extension_loaded = True
    ffi = cffi.FFI()

except ImportError:
    clang_extension_loaded = False
    inside_polygon_ext = None

INT_LIST_REP: Final[str] = "int []"


def pt_in_poly_clang(x: int, y: int, coords: np.ndarray) -> bool:
    """wrapper of the point in polygon test algorithm C extension

    ATTENTION: both rows of ``coords`` must be C-contiguous, which the per-axis
    coordinate layout ([x0...xN-1, y0...yN-1]) gives for free. Read-only input is
    fine - the buffer is only read. A strided row raises
    ``ValueError: ndarray is not C-contiguous`` instead of being copied into shape:
    a silent copy here would reintroduce a per-call allocation on every point in
    polygon test with no test able to observe it.
    """
    if ffi is None:
        raise ValueError(
            "Trying to use the clang implementation of the point in polygon algorithm "
            "while the C extension in not loaded."
        )
    x_coords = coords[0]
    y_coords = coords[1]
    nr_coords = len(x_coords)

    # The ignores below work around a stub gap, not a real mismatch: `types-cffi`
    # declares `from_buffer`'s second argument as `_typeshed.Buffer`, which the
    # numpy stubs do not advertise on `np.ndarray` even though it implements the
    # buffer protocol at runtime.
    x_coords_ffi = ffi.from_buffer(INT_LIST_REP, x_coords)  # type: ignore[call-overload]
    y_coords_ffi = ffi.from_buffer(INT_LIST_REP, y_coords)  # type: ignore[call-overload]
    contained = inside_polygon_ext.lib.inside_polygon_int(
        x, y, nr_coords, x_coords_ffi, y_coords_ffi
    )
    return contained
