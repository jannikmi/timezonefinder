#!/usr/bin/env python
"""
Test script to verify that the resource management improvements work correctly.
"""

import gc
import sys
import weakref

import numpy as np
import pytest

from timezonefinder import TimezoneFinder, TimezoneFinderL
from timezonefinder.block_payload import PAYLOAD_WORD_DTYPE
from timezonefinder.coord_accessors import FileCoordAccessor
from timezonefinder.flatbuf.io.polygons import get_coordinate_path
from timezonefinder.utils import close_resource, get_boundaries_dir


@pytest.mark.unit
def test_declared_slots_are_assigned():
    """Every declared slot must be assigned by some finder.

    ``__slots__`` is here to forbid stray attributes, so a slot no code ever assigns is
    not merely dead - it re-permits the one attribute it names, punching a hole in that
    guarantee. Four leftovers (``in_memory``, ``_fromfile``, ``_boundaries_file``,
    ``_holes_file``) survived a refactor because nothing checked.

    The union is taken across both concrete classes on purpose: the base declares slots
    that only ``TimezoneFinder`` assigns, so neither class satisfies the list alone.
    """
    finder_classes = (TimezoneFinder, TimezoneFinderL)

    declared = {
        name
        for finder_cls in finder_classes
        for klass in finder_cls.__mro__
        for name in getattr(klass, "__slots__", ())
    }

    assigned = set()
    for finder_cls in finder_classes:
        with finder_cls() as finder:
            assigned |= {name for name in declared if hasattr(finder, name)}

    assert declared == assigned, (
        f"slots declared but never assigned: {sorted(declared - assigned)}"
    )


def test_context_manager_usage():
    """Test that context managers work properly for resource management."""
    print("Testing context manager functionality...")

    # Test TimezoneFinder basic functionality
    with TimezoneFinder() as tf:
        result = tf.timezone_at(lng=-74.0059, lat=40.7128)  # New York
        print(f"New York timezone: {result}")
        assert result == "America/New_York"

    print("✓ TimezoneFinder context manager works")


def test_resource_cleanup_after_exception():
    """Test that resources are properly cleaned up even after exceptions."""
    print("Testing resource cleanup after exceptions...")

    try:
        with TimezoneFinder() as tf:
            # Test normal operation first
            result = tf.timezone_at(lng=0, lat=0)
            print(f"Timezone at (0,0): {result}")

            # Now raise an exception
            raise ValueError("Test exception")
    except ValueError as e:
        print(f"Caught expected exception: {e}")

    print("✓ Resources cleaned up properly after exception")


@pytest.mark.unit
class TestNumpyViewOutlivesAccessor:
    """Polygon arrays are zero-copy views onto the memory-mapped coordinate file.

    When such a view outlives the accessor, ``mmap.close()`` raises
    ``BufferError: cannot close exported pointers exist``. That is a safety guarantee -
    unmapping while views reference the memory would leave them dangling - and must not
    surface as an error during teardown.
    """

    @staticmethod
    def _accessor() -> FileCoordAccessor:
        return FileCoordAccessor(get_coordinate_path(get_boundaries_dir()))

    def test_returned_array_is_a_view_onto_the_mmap(self):
        """Guard the precondition: if this ever becomes a copy, the tests below are moot."""
        accessor = self._accessor()
        try:
            coords = accessor[0]
            assert not coords.flags["OWNDATA"]
        finally:
            accessor.cleanup()

    def test_returned_payload_is_contiguous(self):
        """A ring's payload is a dense run of words inside the collection's buffer.

        Both acceleration backends depend on it: the C extension rejects a strided
        buffer outright, and the Numba kernel's eager signature is C-ordered. A view
        that went back to being strided would reintroduce a per-call copy silently.
        """
        accessor = self._accessor()
        try:
            payload = accessor[0]
            assert payload.dtype == PAYLOAD_WORD_DTYPE
            assert payload.flags["C_CONTIGUOUS"]
            assert accessor.words.flags["C_CONTIGUOUS"]
        finally:
            del payload
            accessor.cleanup()

    def test_cleanup_with_live_view_does_not_raise(self):
        """Explicit cleanup() must not propagate the BufferError from mmap.close()."""
        accessor = self._accessor()
        payload = accessor[0]  # keeps a view onto the mmap alive

        accessor.cleanup()  # used to raise BufferError

        # the view is still valid: suppressing the error kept the mapping alive
        assert payload.ndim == 1
        assert payload.size > 0

    def test_cleanup_releases_mapping_once_the_view_is_dropped(self):
        """A refused close must only defer the unmapping, not pin it to the accessor.

        cleanup() drops its own references to the mmap, so the mapping goes away with
        the last view even if the accessor itself is still alive.
        """
        accessor = self._accessor()
        coords = accessor[0]
        mmap_alive = weakref.ref(accessor.coord_buf)

        accessor.cleanup()
        assert mmap_alive() is not None, "view is alive, so the mapping must persist"

        del coords
        gc.collect()

        assert mmap_alive() is None, (
            "mapping still held after the last view was dropped"
        )
        # keep the accessor referenced to prove it is not what released the mapping
        assert accessor is not None

    def test_repeated_cleanup_with_live_view_does_not_raise(self):
        """cleanup() runs again via __del__, so it must stay idempotent."""
        accessor = self._accessor()
        coords = accessor[0]

        accessor.cleanup()
        accessor.cleanup()

        assert coords.size > 0

    def test_view_outlives_timezonefinder_without_unraisable_error(self):
        """The reported case: a polygon array outliving the TimezoneFinder instance.

        Teardown happens in __del__, where exceptions do not propagate but are reported
        via sys.unraisablehook - so capture those instead of relying on pytest's plugin.
        """
        tf = TimezoneFinder()
        coords = tf.coords_of(0)
        expected = np.array(coords, copy=True)

        unraisable = []
        original_hook = sys.unraisablehook
        sys.unraisablehook = unraisable.append
        try:
            del tf
            gc.collect()
        finally:
            sys.unraisablehook = original_hook

        # the message is only evaluated on failure, so indexing is safe here
        assert not unraisable, f"exception escaped __del__: {unraisable[0].exc_value!r}"
        # the mapping outlived the accessor, so the data is still intact
        assert np.array_equal(coords, expected)

    def test_close_resource_suppresses_buffer_error(self):
        """BufferError is treated like the other expected close() failures."""

        class RefusesToClose:
            def close(self):
                raise BufferError("cannot close exported pointers exist")

        close_resource(RefusesToClose())  # must not raise


@pytest.mark.unit
def test_shortcut_arrays_do_not_pin_the_file_buffer(hybrid_shortcuts):
    """The opposite contract to ``TestNumpyViewOutlivesAccessor`` above.

    Polygon coordinates are deliberately views onto the memory map. A cell's candidate
    polygon ids must *not* be views onto the shortcut file's ``bytes``: an earlier reader
    handed those out, so a few tens of KB of live ids pinned the whole binary for the
    lifetime of every finder instance.
    """

    def owner_of(arr: np.ndarray) -> object:
        while isinstance(arr.base, np.ndarray):
            arr = arr.base
        return arr if arr.base is None else arr.base

    arrays = [v for v in hybrid_shortcuts.values() if isinstance(v, np.ndarray)]
    assert arrays, "fixture holds no polygon lists - the assertions below are vacuous"

    owners = {id(owner_of(arr)): owner_of(arr) for arr in arrays}
    assert len(owners) == 1, f"expected one shared buffer, got {len(owners)}"
    (owner,) = owners.values()
    # what the owner *is* does not matter - its size does. The whole file would satisfy
    # every other assertion here, and is what this used to hand out. It is *smaller* than
    # the slices referencing it because identical candidate lists are stored once, so
    # several cells point into one range.
    retained = owner.nbytes if isinstance(owner, np.ndarray) else len(owner)
    assert retained <= sum(arr.nbytes for arr in arrays), (
        f"the {retained} B buffer behind the poly ids retains more than the "
        f"{sum(arr.nbytes for arr in arrays)} B referencing it"
    )
    assert not any(arr.flags["WRITEABLE"] for arr in arrays), (
        "shared backing array must not be writeable through its slices - cells with "
        "identical candidate lists share one range of it"
    )


@pytest.mark.unit
@pytest.mark.parametrize("in_memory", [False, True])
def test_loaded_dataset_arrays_are_read_only(in_memory):
    """Publicly reachable dataset state must not be mutable by accident.

    These arrays feed later lookups directly. An assignment used to succeed and silently
    changed their answers; the coordinate arrays were already read-only because their
    backing bytes are immutable, so include them to pin one contract across both storage
    modes.
    """
    with TimezoneFinder(in_memory=in_memory) as finder:
        arrays = {
            "zone_ids": finder.zone_ids,
            **{
                f"shortcuts.{name}": getattr(finder.shortcuts, name)
                for name in ("table", "starts", "ends", "last_change", "payload")
            },
            **{
                f"boundaries.{name}": getattr(finder.boundaries, name)
                for name in ("xmin", "xmax", "ymin", "ymax")
            },
            **{
                f"holes.{name}": getattr(finder.holes, name)
                for name in ("xmin", "xmax", "ymin", "ymax", "poly_ref")
            },
            "boundary coordinates": finder.boundaries.coords_of(0),
            "hole coordinates": finder.holes.coords_of(0),
        }
        if not in_memory:
            arrays.update(
                {
                    "boundary payload offsets": (
                        finder.boundaries.coordinates.word_offsets
                    ),
                    "boundary payload lengths": (
                        finder.boundaries.coordinates.word_lengths
                    ),
                    "hole payload offsets": finder.holes.coordinates.word_offsets,
                    "hole payload lengths": finder.holes.coordinates.word_lengths,
                }
            )

        # Materialise the lazy names gather too: it is runtime dataset state, while the
        # array returned by a public batch lookup remains a fresh, writeable result.
        finder.zone_names.names_of(np.zeros(128, dtype=np.int32))
        assert finder.zone_names._gather_lookup is not None
        arrays["zone-name gather"] = finder.zone_names._gather_lookup

        for name, array in arrays.items():
            assert not array.flags.writeable, name
            with pytest.raises(ValueError, match="read-only"):
                array.flat[0] = array.flat[0]
