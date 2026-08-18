"""Integrity checks over a *compiled* binary data directory.

These run where the data is produced and where it is reviewed - the converter checks
what it just wrote, and the test suite checks what the repository ships. They are
deliberately **not** run when a ``TimezoneFinder`` is constructed: whether a data
directory is coherent is settled once, by the build, and re-deriving it in every user's
process would spend startup time re-answering a question that already has an answer.

What that buys is the freedom to check properly. Nothing here is written to be cheap:
the reference check resolves every hole ring and compares its extent against the stored
bounding box, which is O(all hole vertices) and would be indefensible on an
initialisation path.
"""

from pathlib import Path

from scripts.configs import MIN_HOLE_DEDUP_RATIO
from timezonefinder.flatbuf.schemas import (
    SCHEMA_SUFFIX,
    get_schemas_dir,
    iter_schema_files,
)
from timezonefinder.np_binary_helpers import get_poly_ref_path
from timezonefinder.polygon_array import HoleArray, PolygonArray
from timezonefinder.utils import get_boundaries_dir, get_holes_dir


class DataIntegrityError(ValueError):
    """A compiled data directory is internally inconsistent."""


def validate_hole_references(data_dir: Path) -> None:
    """Check that the hole reference encoding in ``data_dir`` addresses real geometry.

    A hole is stored either as its own ring or as a reference to the identical boundary
    polygon (see ``docs/data_format.rst``). The reference vector, the hole coordinate
    file and the hole bounding box vectors are three separate files, so they can only be
    trusted together if something checks that they agree. Nothing about a disagreement
    is self-announcing: every hole id still resolves to *some* valid ring, so the
    symptom is a plausible wrong timezone rather than an error.

    :param data_dir: A compiled data directory, as written by ``scripts/file_converter.py``
    :raises DataIntegrityError: if the hole files do not agree with each other
    """
    boundaries = PolygonArray(data_location=get_boundaries_dir(data_dir))
    holes_dir = get_holes_dir(data_dir)
    holes = HoleArray(data_location=holes_dir, boundaries=boundaries)

    nr_holes = len(holes)
    nr_stored = len(holes.coordinates)
    poly_ref = holes.poly_ref
    ref_path = get_poly_ref_path(holes_dir)

    if len(poly_ref) != nr_holes:
        raise DataIntegrityError(
            f"{ref_path} has {len(poly_ref)} entries but there are {nr_holes} holes."
        )

    inline_positions = sorted(-(int(v) + 1) for v in poly_ref if v < 0)
    if inline_positions != list(range(nr_stored)):
        raise DataIntegrityError(
            f"{ref_path} does not address each of the {nr_stored} inline rings in "
            f"{holes_dir} exactly once."
        )

    if nr_holes:
        max_ref = int(poly_ref.max())
        if max_ref >= len(boundaries):
            raise DataIntegrityError(
                f"a hole in {holes_dir} references boundary polygon {max_ref}, but only "
                f"{len(boundaries)} boundary polygons exist."
            )

    # The strongest check available, and the only one with evidence independent of the
    # references themselves: the bounding boxes are computed from the original hole
    # rings before deduplication and never rewritten, so a reference pointing at the
    # wrong polygon resolves to a ring whose extent disagrees with them.
    for hole_id in range(nr_holes):
        ring = holes.coords_of(hole_id)
        expected = (
            int(holes.xmin[hole_id]),
            int(holes.xmax[hole_id]),
            int(holes.ymin[hole_id]),
            int(holes.ymax[hole_id]),
        )
        actual = (
            int(ring[0].min()),
            int(ring[0].max()),
            int(ring[1].min()),
            int(ring[1].max()),
        )
        if expected != actual:
            ref = int(poly_ref[hole_id])
            target = (
                f"boundary polygon {ref}" if ref >= 0 else f"inline ring {-(ref + 1)}"
            )
            raise DataIntegrityError(
                f"hole {hole_id} in {holes_dir} resolves to {target}, whose extent "
                f"{actual} does not match the bounding box {expected} stored for it. "
                f"The reference points at the wrong geometry."
            )


def validate_hole_dedup_ratio(data_dir: Path) -> None:
    """Check that deduplication is still paying off for a full timezone dataset.

    Kept separate from :func:`validate_hole_references`, which is about whether the
    files agree with each other and holds for *any* data directory. This one is an
    expectation about the upstream data - that the boundary builder still emits
    enclaves as shared rings - and it is only meaningful at dataset scale. A small
    custom region legitimately has few enclaves and would fail it while being perfectly
    well formed.

    The converter only reports the ratio - compiling custom data whose holes are not
    enclaves is a supported use case. This is where it is actually enforced, and it is
    applied to the packaged dataset alone.

    :param data_dir: A compiled data directory
    :raises DataIntegrityError: if too few holes are stored as references
    """
    boundaries = PolygonArray(data_location=get_boundaries_dir(data_dir))
    holes_dir = get_holes_dir(data_dir)
    holes = HoleArray(data_location=holes_dir, boundaries=boundaries)
    if not len(holes):
        return

    ratio = int((holes.poly_ref >= 0).sum()) / len(holes)
    if ratio < MIN_HOLE_DEDUP_RATIO:
        raise DataIntegrityError(
            f"only {ratio:.1%} of the holes in {holes_dir} are stored as a reference "
            f"to an identical boundary polygon, below the expected minimum of "
            f"{MIN_HOLE_DEDUP_RATIO:.0%}. Either the upstream dataset stopped emitting "
            f"enclaves as shared rings - in which case the packaged data is quietly "
            f"re-inflated - or the matching pass is broken. Re-check with "
            f"prototypes/hole_boundary_redundancy.py."
        )


def validate_shipped_schemas(data_dir: Path) -> None:
    """Check that the schemas in ``data_dir`` are the ones its binaries were written by.

    A compiled data directory carries a copy of the FlatBuffers schemas describing it,
    so that it says what its own format is - which matters for a hand-built
    ``bin_file_location`` and for anyone debugging one, and puts the format's definition
    in the distribution whose major version *is* the format version.

    Being a copy, it can go stale: the schemas change under ``make flatbuf`` while the
    binaries are not regenerated, and nothing about the resulting directory announces
    that the description no longer matches the thing described. Hence one check, run
    both by the converter over what it just wrote and by the test suite over what is
    committed.

    :param data_dir: A compiled data directory, as written by ``scripts/file_converter.py``
    :raises DataIntegrityError: if the shipped schemas are missing or differ
    """
    shipped_dir = get_schemas_dir(data_dir)
    expected = {path.name: path.read_bytes() for path in iter_schema_files()}
    if not expected:
        raise DataIntegrityError(
            "no schema definitions found to compare against - the canonical schemas "
            "have moved, and the shipped copies are now checked against nothing."
        )

    shipped = {
        path.name: path.read_bytes()
        for path in sorted(shipped_dir.glob(f"*{SCHEMA_SUFFIX}"))
    }
    if shipped.keys() != expected.keys():
        missing = sorted(expected.keys() - shipped.keys())
        extra = sorted(shipped.keys() - expected.keys())
        raise DataIntegrityError(
            f"{shipped_dir} does not hold the schemas describing this data: "
            f"missing {missing}, unexpected {extra}. Regenerate the data directory."
        )

    differing = sorted(name for name, body in expected.items() if shipped[name] != body)
    if differing:
        raise DataIntegrityError(
            f"the schema copies in {shipped_dir} differ from the canonical ones: "
            f"{differing}. They are generated, so fix this by regenerating the data "
            "rather than by editing the copy - and check whether the binaries next to "
            "it still match the schema that changed."
        )
