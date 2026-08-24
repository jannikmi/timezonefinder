"""
The timezone names: their file, and turning zone ids back into them.

A zone id is an index into this list and nothing more, so naming one is a lookup rather
than part of finding a timezone - which is why :class:`ZoneNames` lives here, next to
the file it reads, rather than on the finder. The finder produces ids; this names them.
"""

from pathlib import Path
from typing import Final

import numpy as np

from timezonefinder.configs import DEFAULT_DATA_DIR, IdArrayLike, NO_ZONE_ID

__all__ = [
    "get_zone_names_path",
    "write_zone_names",
    "read_zone_names",
    "ZoneNames",
    "NAMES_GATHER_MIN_BATCH",
]

#: Batch size from which converting zone ids to names through a numpy gather beats a
#: Python loop. Measured, not guessed - min ns per id over uniformly random fixture
#: points, with 10 % of the ids being the sentinel, on one machine:
#:
#: ======  ========  ======
#: N       loop      gather
#: ======  ========  ======
#: 10      33.4      316.6
#: 64      30.6      56.0
#: **128** **31.2**  **31.9**
#: 256     33.7      19.4
#: 10,000  38.8      7.6
#: ======  ========  ======
#:
#: numpy's per-call overhead is what dominates a short batch, so below the crossover the
#: gather is up to 16x *worse* per id and above it up to 5x better. The threshold does not
#: have to be exact on another machine: near it the two are within a few percent of each
#: other by definition, which is what makes a single constant safe here.
NAMES_GATHER_MIN_BATCH: Final[int] = 128


def get_zone_names_path(output_path: Path = DEFAULT_DATA_DIR) -> Path:
    """
    Get the absolute path to the timezone names file.

    :param output_path: Directory containing the timezone names file (default: package data dir)
    :return: Path to timezone_names.txt
    """
    return output_path / "timezone_names.txt"


def write_zone_names(zone_names: list[str], output_path: Path) -> None:
    """
    Write timezone names to a persistent text file.

    The file format is one timezone name per line. This is used during data generation to
    store the list of all timezone identifiers in the dataset.

    :param zone_names: List of timezone names to write
    :param output_path: Directory where output file will be written. Required, unlike
        the read side above: ``DEFAULT_DATA_DIR`` resolves to wherever the
        ``timezonefinder-data`` distribution is installed, so defaulting to it would
        make an omitted argument rewrite the installed dataset in site-packages.
        Generators pass ``scripts.configs.SOURCE_DATA_DIR``.
    :raises OSError: If file cannot be written
    """
    path = get_zone_names_path(output_path)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(zone_names))
        f.write("\n")  # write a newline at the end of the file


def read_zone_names(path: Path) -> list[str]:
    """
    Read timezone names from the persistent text file.

    The file should contain one timezone name per line. Empty lines are skipped.

    :param path: Directory containing the timezone names file
    :return: List of timezone names, in zone id order
    :raises FileNotFoundError: If the directory holds no timezone names file
    :raises OSError: For any other read failure (``FileNotFoundError`` is a subclass of it,
        listed separately because it is the one a caller realistically handles)

    Example:
        >>> names = read_zone_names(Path("./data"))
        >>> "Europe/Berlin" in names
        True
    """
    file_path = get_zone_names_path(path)
    with open(file_path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


class ZoneNames:
    """The dataset's timezone names, and every way a zone id is turned into one.

    Held by a finder rather than inherited from it: naming an id touches no coordinate,
    no shortcut and no polygon, so keeping it here is what stops the lookup module from
    also owning a string table, a lazily built gather array and a tuning constant for it.

    Instances are per-thread by contract, as finders are.
    """

    __slots__ = ("names", "_gather_lookup")

    def __init__(self, names: list[str]):
        #: the names in zone id order - a plain list, because it is public API on the
        #: finder and callers index, iterate and ``.index()`` it
        self.names: list[str] = names
        # built on first use rather than here, so a finder that never converts a large
        # batch of ids allocates nothing for it - construction heap and resident set are
        # what `docs/benchmark_results_memory.rst` measures, and a lightweight finder's
        # whole footprint is small enough that ~450 object pointers would show
        self._gather_lookup: np.ndarray | None = None

    def __len__(self) -> int:
        return len(self.names)

    def name_of(self, zone_id: int) -> str:
        """Look up one name without checking the id's sign.

        The unchecked accessor the query path uses: every id reaching it came from the
        shortcut index or from ``zone_ids``, neither of which can hold a negative value.
        """
        try:
            return self.names[zone_id]
        except IndexError as e:
            raise ValueError(
                f"Zone ID {zone_id} is out of range. "
                f"Valid range: 0-{len(self.names) - 1}. "
                f"Loaded dataset has {len(self.names)} timezones."
            ) from e

    def _lookup_array(self) -> np.ndarray:
        """The names as an object array with ``None`` appended, built once per instance.

        The trailing ``None`` is what makes the gather need no masking:
        :data:`~timezonefinder.configs.NO_ZONE_ID` is ``-1``, so it indexes the last
        element by Python's own negative-index rule. That is the same "counts from the
        end" behaviour the public id-taking methods reject - deliberate here, because
        here the end *is* the sentinel, and every other negative is rejected before the
        gather runs.

        Even a race would build an identical array twice and assign the same content, so
        no lock is warranted.
        """
        lookup = self._gather_lookup
        if lookup is None:
            lookup = np.asarray([*self.names, None], dtype=object)
            self._gather_lookup = lookup
        return lookup

    def names_of(self, zone_ids: np.ndarray) -> list[str | None]:
        """Names for zone ids already known to be valid.

        Two regimes, because neither wins everywhere - see
        :data:`NAMES_GATHER_MIN_BATCH` for the measurement that sets the boundary.
        """
        if zone_ids.shape[0] < NAMES_GATHER_MIN_BATCH:
            names = self.names
            return [
                None if zone_id < 0 else names[zone_id] for zone_id in zone_ids.tolist()
            ]
        return self._lookup_array()[zone_ids].tolist()

    def names_from_ids(self, zone_ids: IdArrayLike) -> list[str | None]:
        """Validate a batch of ids and name them.

        The checked entry point, for ids this package did not just produce itself.

        :raises TypeError: if ``zone_ids`` does not hold integers.
        :raises ValueError: if ``zone_ids`` is not one-dimensional, or holds an id that
            is neither a valid zone id nor the sentinel.
        """
        ids = np.asarray(zone_ids)
        # the shape is checked before the size, so that a wrongly shaped input is
        # rejected on the empty run too - otherwise an (N, 2) array is accepted while it
        # happens to be empty and only raises once real data arrives
        if ids.ndim != 1:
            raise ValueError(f"zone_ids must be one-dimensional, got shape {ids.shape}")
        if ids.size == 0:
            # an empty list arrives as float64, which is not an error to convert
            return []
        if not np.issubdtype(ids.dtype, np.integer):
            raise TypeError(
                f"zone ids must be integers, got dtype {ids.dtype}. "
                f"An id is an index into the {len(self.names)} loaded timezone names."
            )
        # one pass for both bounds: below the sentinel, or past the last zone. The upper
        # half is not redundant with numpy's own IndexError - the lookup array carries one
        # extra slot for the sentinel, so the zone count itself would quietly read it.
        invalid = (ids < NO_ZONE_ID) | (ids >= len(self.names))
        if invalid.any():
            offender = int(ids[invalid][0])
            raise ValueError(
                f"{offender} is not a valid zone id. Valid range: "
                f"0-{len(self.names) - 1}, or {NO_ZONE_ID} for 'no zone'. "
                f"Loaded dataset has {len(self.names)} timezones."
            )
        return self.names_of(ids)
