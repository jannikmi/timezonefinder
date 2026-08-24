#!/usr/bin/env python3

"""How often this package and ``tzfpy`` return a different zone, and why.

What this answers, and what it deliberately does not
----------------------------------------------------

``docs/alternatives.rst`` states that ``tzfpy`` ships simplified polygons and
trades accuracy near borders for size and speed. Nothing in this repository
said what that trade *costs*, which is the question `issue #542
<https://github.com/jannikmi/timezonefinder/issues/542>`__ has to answer before
the polygon encoding can be chosen: this package spends ~1.1 cm of coordinate
resolution, and there is no evidence anywhere about what that resolution is
worth.

This is the competitor half of that evidence. It measures where the most-used
alternative sits on the size/accuracy axis - not what any user needs, which is
a separate measurement requiring the shortcut index rebuilt from quantized
geometry.

Two things make the number mean something, and without either it would not
-------------------------------------------------------------------------

**The boundary release has to match.** Both packages compile
timezone-boundary-builder output, and a disagreement between two *releases*
says nothing about geometry - a border genuinely moved. So this refuses to
report unless ``tzfpy.data_version()`` equals the release this repository
packages. When they match, this package answers from the source polygons and
``tzfpy`` from a simplification of the same polygons, which is what makes a
disagreement attributable to the simplification.

**Overlapping zones have to be separated out.** The dataset ships genuinely
overlapping polygons - ``Asia/Urumqi`` inside ``Asia/Shanghai`` is the large
one - and each package picks one answer from the overlap by its own rule.
Comparing ``timezone_at`` against ``tzfpy.get_tz`` counts every such point as a
disagreement, and they dominate the raw rate while saying nothing about
geometry. Asking instead whether our answer appears in ``tzfpy.get_tzs`` - the
full set of zones it holds over that point - is the rate that describes the
geometry, and it is the one to quote.

Usage::

    make tzfpy-agreement
    uv run --group compare python -m scripts.measure_tzfpy_agreement
"""

import argparse
import json
import sys
from typing import Callable, Iterable, NamedTuple, Sequence

from scripts.benchmark_utils import TZFPY_DISTRIBUTION, tzfpy_version
from scripts.configs import read_data_version
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder

# The committed point fixtures, in the order the report prints them: two
# workload-shaped classes first, then the two that say where any difference
# comes from. `ambiguous_shortcut` is the closest thing to a near-border
# sample this repository has - its points sit in an H3 cell holding more than
# one candidate zone - but an H3 resolution 4 cell is tens of kilometres
# across, so it is a proxy for "near a border" and not a sample *at* one. It
# bounds the rate from below, never from above.
POINT_CLASSES: tuple[str, ...] = (
    RANDOM_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
)

# How a single point's two answers relate. `OVERLAP_POLICY` is the case the
# module docstring exists for: both packages hold our zone over the point and
# merely disagree about which of the overlapping zones to name.
AGREE = "agree"
OVERLAP_POLICY = "overlap_policy"
SUBSTANTIVE = "substantive"


# How many substantive disagreements to keep per point class. A bare count is
# unattributable - three points out of five thousand could be a coastline, a
# pole, or a bug in this script - so the report names some of them.
MAX_EXAMPLES = 5


class AgreementCounts(NamedTuple):
    """One point class, counted three ways, with a few cases named."""

    total: int
    overlap_policy: int
    substantive: int
    examples: tuple[tuple[float, float, str | None, tuple[str, ...]], ...] = ()

    @property
    def first_answer_disagreements(self) -> int:
        """What comparing ``timezone_at`` against ``get_tz`` alone would report."""
        return self.overlap_policy + self.substantive

    def rate(self, count: int) -> float:
        return 100.0 * count / self.total if self.total else 0.0


def classify(
    ours: str | None, theirs_first: str | None, theirs_all: Sequence[str]
) -> str:
    """Relate one point's two answers.

    Split out from the measurement loop because it is the whole of the
    interpretation, and it needs no ``tzfpy`` to test: everything else here is
    counting.
    """
    if ours == theirs_first:
        return AGREE
    if ours is not None and ours in theirs_all:
        # they hold our zone over this point too, and picked a different one of
        # the zones overlapping there
        return OVERLAP_POLICY
    return SUBSTANTIVE


def count_agreement(
    points: Iterable[tuple[float, float]],
    ours: Callable[[float, float], str | None],
    theirs_first: Callable[[float, float], str | None],
    theirs_all: Callable[[float, float], Sequence[str]],
) -> AgreementCounts:
    total = overlap = substantive = 0
    examples: list[tuple[float, float, str | None, tuple[str, ...]]] = []
    for lng, lat in points:
        total += 1
        our_answer = ours(lng, lat)
        their_zones = tuple(theirs_all(lng, lat))
        verdict = classify(our_answer, theirs_first(lng, lat), their_zones)
        if verdict == OVERLAP_POLICY:
            overlap += 1
        elif verdict == SUBSTANTIVE:
            substantive += 1
            if len(examples) < MAX_EXAMPLES:
                examples.append((lng, lat, our_answer, their_zones))
    return AgreementCounts(
        total=total,
        overlap_policy=overlap,
        substantive=substantive,
        examples=tuple(examples),
    )


def _require_matching_dataset(tzfpy) -> str:
    """The guard the whole measurement rests on - see the module docstring."""
    ours = read_data_version()
    theirs = tzfpy.data_version()
    if ours != theirs:
        raise SystemExit(
            f"{TZFPY_DISTRIBUTION} {tzfpy_version()} packages boundary release "
            f"{theirs!r}, this repository packages {ours!r}. A disagreement "
            "between two releases is a border that moved, not geometry that was "
            "simplified, so there is no measurement to take until the two match."
        )
    return ours


class Measurement(NamedTuple):
    """One run: which data both sides answered from, and the counts."""

    data_version: str
    tzfpy_version: str | None
    per_class: dict[str, AgreementCounts]

    def as_json(self) -> dict:
        return {
            "data_version": self.data_version,
            "tzfpy_version": self.tzfpy_version,
            "counts": {
                name: counts._asdict() for name, counts in self.per_class.items()
            },
        }


def measure() -> Measurement:
    import tzfpy

    data_version = _require_matching_dataset(tzfpy)
    with TimezoneFinder(in_memory=True) as finder:
        per_class = {
            name: count_agreement(
                load_benchmark_points(name),
                lambda lng, lat: finder.timezone_at(lng=lng, lat=lat),
                tzfpy.get_tz,
                tzfpy.get_tzs,
            )
            for name in POINT_CLASSES
        }
    return Measurement(
        data_version=data_version,
        tzfpy_version=tzfpy_version(),
        per_class=per_class,
    )


def format_report(measurement: Measurement) -> str:
    lines = [
        f"boundary release {measurement.data_version} on both sides "
        f"({TZFPY_DISTRIBUTION} {measurement.tzfpy_version})",
        "",
        f"{'point class':<26}{'n':>7}{'substantive':>18}{'overlap-policy':>18}",
    ]
    for name, counts in measurement.per_class.items():
        lines.append(
            f"{name:<26}{counts.total:>7}"
            f"{counts.substantive:>11} {counts.rate(counts.substantive):>5.3f}%"
            f"{counts.overlap_policy:>11} {counts.rate(counts.overlap_policy):>5.3f}%"
        )
    named = [
        (name, example)
        for name, counts in measurement.per_class.items()
        for example in counts.examples
    ]
    if named:
        lines += ["", "substantive disagreements, by example:"]
        lines += [
            f"  {name}: ({lng:.5f}, {lat:.5f}) -> {ours!r}, {TZFPY_DISTRIBUTION} holds "
            f"{list(theirs)}"
            for name, (lng, lat, ours, theirs) in named
        ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the counts as JSON instead of a table",
    )
    args = parser.parse_args(argv)

    measurement = measure()
    if args.json:
        print(json.dumps(measurement.as_json(), indent=2))
    else:
        print(format_report(measurement))
    return 0


if __name__ == "__main__":
    sys.exit(main())
