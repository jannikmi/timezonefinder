from typing import Any, Final

import cffi

import numpy as np

ffi: cffi.FFI | None = None
# declared before the import so the two branches agree on one type. The extension is a
# cffi C extension with no stubs, and the fallback is ``None``; without this mypy joins
# them and rejects every ``.lib`` access below on the ``None`` half.
inside_polygon_ext: Any = None
try:
    # Note: IDE might complain as this import comes from a cffi C extension
    from timezonefinder import inside_polygon_ext  # type: ignore[no-redef]

    clang_extension_loaded = True
    ffi = cffi.FFI()

except ImportError:
    clang_extension_loaded = False

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


#: How the packed payload and the per-block columns reach the C kernel. Named for the
#: same reason ``INT_LIST_REP`` is: ``ffi.from_buffer`` takes the element type as a
#: string, and a wrong one here would reinterpret the buffer rather than fail.
UCHAR_LIST_REP: Final[str] = "unsigned char []"
UINT_LIST_REP: Final[str] = "unsigned int []"


def packed_buffers_clang(
    payload: np.ndarray,
    block_ranges: np.ndarray,
    block_bases: np.ndarray,
    block_widths: np.ndarray,
    block_payload_offsets: np.ndarray,
) -> tuple:
    """Wrap a collection's packed arrays once, for :func:`pt_in_poly_clang_packed`.

    ``ffi.from_buffer`` costs ~0.30 us, a fifth of a whole point-in-polygon test, so
    these are built when a collection is loaded rather than per call - which is what
    the kernel taking collection-wide arrays and a ``block_start`` is for. Wrapping
    copies nothing and faults no mapping in, but it does keep the buffers alive, which
    is why ``FileCoordAccessor.cleanup`` drops them before closing the mapping.

    ATTENTION: every array must be C-contiguous, as for :func:`pt_in_poly_clang`. Here
    that holds by construction - each is one array per collection, never a slice.
    """
    if ffi is None:
        raise ValueError(
            "Trying to use the clang implementation of the point in polygon algorithm "
            "while the C extension in not loaded."
        )
    # See pt_in_poly_clang for why these ignores are stub gaps rather than mismatches.
    return (
        ffi.from_buffer(UINT_LIST_REP, payload),  # type: ignore[call-overload]
        ffi.from_buffer(INT_LIST_REP, block_ranges),  # type: ignore[call-overload]
        ffi.from_buffer(INT_LIST_REP, block_bases),  # type: ignore[call-overload]
        ffi.from_buffer(UCHAR_LIST_REP, block_widths),  # type: ignore[call-overload]
        ffi.from_buffer(UINT_LIST_REP, block_payload_offsets),  # type: ignore[call-overload]
    )


def pt_in_poly_clang_packed(
    x: int,
    y: int,
    nr_coords: int,
    block_size: int,
    block_start: int,
    nr_blocks: int,
    payload,
    block_ranges,
    block_bases,
    block_widths,
    block_payload_offsets,
) -> bool:
    """wrapper of the packed point in polygon test algorithm C extension

    :func:`pt_in_poly_clang_blocked` over the bit-packed payload of polygon layout 3
    instead of over an ``int32`` coordinate array. ``timezonefinder/utils_numba.py``'s
    ``pt_in_poly_packed`` documents the arguments, why testing a block in its own
    coordinate frame gives the same answer, and why the arrays belong to the collection
    rather than to the ring.

    The five buffer arguments are what :func:`packed_buffers_clang` wrapped, not arrays:
    this wrapper does no work at all beyond the call itself, which is the point of it.
    """
    if ffi is None:
        raise ValueError(
            "Trying to use the clang implementation of the point in polygon algorithm "
            "while the C extension in not loaded."
        )
    contained = inside_polygon_ext.lib.inside_polygon_packed_int(
        x,
        y,
        nr_coords,
        block_size,
        block_start,
        nr_blocks,
        payload,
        block_ranges,
        block_bases,
        block_widths,
        block_payload_offsets,
    )
    return contained
