"""Shared layout guard for the packaged FlatBuffers binaries.

Both binary kinds - the polygon coordinates and the hybrid shortcuts - can change
what they *mean* without changing anything a parse would notice: same schema, same
vector lengths, values still in range. Parsing such a file succeeds and returns wrong
timezones silently, so each writer stamps a file identifier plus a layout version and
each reader rejects what it cannot read. The rejection is worded once, here, so the
two kinds cannot drift into two different error formats.
"""

from pathlib import Path


def incompatible_layout_error(
    file_kind: str,
    found_version: int,
    expected_version: int,
    file_path: Path | None,
) -> ValueError:
    """Build the error raised for packaged data this version cannot read.

    Args:
        file_kind: what the rejected file is, e.g. ``"polygon coordinate file"``.
        found_version: the layout version the file carries. ``0`` covers files
            written before the marker existed, which is what a missing identifier
            reports rather than "corrupt" - that is what such a file actually is
            for everyone who will ever hit this.
        expected_version: the layout version this checkout reads.
        file_path: where the data came from, named in the message. ``None`` for
            in-memory buffers, which have no path to name.
    """
    location = f" {file_path}" if file_path is not None else ""
    return ValueError(
        f"the {file_kind}{location} uses layout version {found_version}, but this "
        f"timezonefinder reads layout version {expected_version}. What the file holds "
        f"differs between the two, and reading it anyway would yield wrong timezones "
        f"rather than an error, so it is rejected. Regenerate this data directory with "
        f"scripts/file_converter.py from the current checkout."
    )
