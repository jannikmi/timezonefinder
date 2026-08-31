"""Integrity expectation that applies only to the packaged upstream dataset."""

from pathlib import Path

from scripts.configs import MIN_HOLE_DEDUP_RATIO
from timezonefinder._data_integrity import DataIntegrityError
from timezonefinder.polygon_array import HoleArray, PolygonArray
from timezonefinder.utils import get_boundaries_dir, get_holes_dir


def validate_hole_dedup_ratio(data_dir: Path) -> None:
    """Check that deduplication is still paying off for a full timezone dataset.

    This is an expectation about timezone-boundary-builder output, not an invariant of
    every compiled directory. Custom data whose holes are ordinary interior rings is
    valid and must not be rejected by the installed ``validate-data`` command.
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
