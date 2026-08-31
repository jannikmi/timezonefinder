#!/usr/bin/env python3

"""Measure what is lost when source boundary coordinates are quantized further.

The packaged geometry preserves the six decimal places published by
timezone-boundary-builder.  Its int32 storage has a seventh decimal place, but
``tests/test_coordinate_precision.py`` establishes that this last digit contains only
floating-point truncation artifacts.  The first precision reduction that can lose real
source information is therefore six decimal places to five.

This measurement gives that coarser candidate every advantage: coordinates are rounded
to nearest, which minimises their maximum displacement, rather than truncated.  It then
rebuilds the complete data directory, including the H3 shortcut index, before comparing
answers.  Reusing the committed shortcut index would silently ask a different question,
because its candidates were derived from the unquantized geometry.

Usage::

    make precision-impact
    uv run python -m scripts.measure_coordinate_precision --help
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import NamedTuple

import numpy as np

from scripts.border_sampling import BorderGeometry, CandidatePair
from scripts.configs import DOC_ROOT, PROJECT_ROOT
from scripts.data_integrity import validate_shortcut_index
from scripts.file_converter import compile_data_files
from scripts.shortcuts import compile_shortcuts
from scripts.timezone_data import (
    HoleCollection,
    PolygonCollection,
    TimezoneData,
    ZoneCollection,
)
from scripts.utils import write_json
from tests.auxiliaries import (
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    RANDOM_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    load_benchmark_points,
)
from timezonefinder import TimezoneFinder
from timezonefinder.configs import (
    COORD2INT_FACTOR,
    DECIMAL_PLACES_SHIFT,
    zone_id_dtype_to_string,
)
from timezonefinder.utils import is_ocean_timezone


SOURCE_DECIMAL_PLACES = 6
DEFAULT_DECIMAL_PLACES = 5
DEFAULT_DISTANCES_M: tuple[float, ...] = (0.1, 0.5, 1.0, 5.0)
DEFAULT_PAIRS = 10_000
DEFAULT_UNIFORM_POINTS = 200_000
DEFAULT_SEED = 20260831
MAX_EXAMPLES = 5

POINT_CLASSES: tuple[str, ...] = (
    RANDOM_POINTS_FIXTURE,
    ON_LAND_POINTS_FIXTURE,
    UNIQUE_SHORTCUT_POINTS_FIXTURE,
    AMBIGUOUS_SHORTCUT_POINTS_FIXTURE,
)

MEASUREMENT_PATH = DOC_ROOT / "coordinate_precision_impact.json"
REPORT_PATH = DOC_ROOT / "coordinate_precision_impact.rst"


class ChangeExample(NamedTuple):
    lng: float
    lat: float
    source_answer: str | None
    quantized_answer: str | None


class AnswerChanges(NamedTuple):
    total: int
    changed: int
    examples: tuple[ChangeExample, ...] = ()

    @property
    def changed_rate(self) -> float:
        return 100.0 * self.changed / self.total if self.total else 0.0


class PairedChanges(NamedTuple):
    total: int
    affected_one_side: int
    affected_both_sides: int
    examples: tuple[ChangeExample, ...] = ()

    @property
    def affected(self) -> int:
        return self.affected_one_side + self.affected_both_sides

    @property
    def affected_rate(self) -> float:
        return 100.0 * self.affected / self.total if self.total else 0.0

    @property
    def upper_bound_rate(self) -> float:
        """95% rule-of-three bound when a finite sample finds no change."""
        return 300.0 / self.total if self.total else 0.0


class DistanceResult(NamedTuple):
    distance_m: float
    drawn: int
    all_borders: PairedChanges
    land_borders: PairedChanges

    @property
    def acceptance_rate(self) -> float:
        return 100.0 * self.all_borders.total / self.drawn if self.drawn else 0.0


class Measurement(NamedTuple):
    data_version: str
    source_decimal_places: int
    tested_decimal_places: int
    quantization: str
    seed: int
    by_distance: tuple[DistanceResult, ...]
    uniform_globe: AnswerChanges
    by_point_class: dict[str, AnswerChanges]

    def as_json(self) -> dict[str, object]:
        return {
            "data_version": self.data_version,
            "source_decimal_places": self.source_decimal_places,
            "tested_decimal_places": self.tested_decimal_places,
            "quantization": self.quantization,
            "seed": self.seed,
            "by_distance_m": [
                {
                    "distance_m": result.distance_m,
                    "drawn": result.drawn,
                    "all_borders": result.all_borders._asdict(),
                    # Land borders are a subset of the all-border population, so their
                    # examples would duplicate the same coordinates without adding
                    # evidence. Keep the separate denominator and count only.
                    "land_borders": result.land_borders._replace(examples=())._asdict(),
                }
                for result in self.by_distance
            ],
            "uniform_globe": self.uniform_globe._asdict(),
            "by_point_class": {
                name: changes._asdict() for name, changes in self.by_point_class.items()
            },
        }

    @classmethod
    def from_json(cls, payload: dict[str, object]) -> Measurement:
        by_distance_payload = payload["by_distance_m"]
        point_class_payload = payload["by_point_class"]
        if not isinstance(by_distance_payload, list) or not isinstance(
            point_class_payload, dict
        ):
            raise TypeError("measurement lists and mappings have the wrong shape")
        return cls(
            data_version=str(payload["data_version"]),
            source_decimal_places=_json_int(payload["source_decimal_places"]),
            tested_decimal_places=_json_int(payload["tested_decimal_places"]),
            quantization=str(payload["quantization"]),
            seed=_json_int(payload["seed"]),
            by_distance=tuple(
                _distance_result_from_json(result) for result in by_distance_payload
            ),
            uniform_globe=_answer_changes_from_json(payload["uniform_globe"]),
            by_point_class={
                str(name): _answer_changes_from_json(changes)
                for name, changes in point_class_payload.items()
            },
        )


def _json_int(value: object) -> int:
    if not isinstance(value, int):
        raise TypeError(f"expected a JSON integer, got {type(value).__name__}")
    return value


def _change_examples(payload: object) -> tuple[ChangeExample, ...]:
    if not isinstance(payload, list):
        raise TypeError("change examples must be a list")
    return tuple(ChangeExample(*example) for example in payload[:MAX_EXAMPLES])


def _answer_changes_from_json(payload: object) -> AnswerChanges:
    if not isinstance(payload, dict):
        raise TypeError("answer-change counts must be a mapping")
    return AnswerChanges(
        total=int(payload["total"]),
        changed=int(payload["changed"]),
        examples=_change_examples(payload["examples"]),
    )


def _paired_changes_from_json(payload: object) -> PairedChanges:
    if not isinstance(payload, dict):
        raise TypeError("paired-change counts must be a mapping")
    return PairedChanges(
        total=int(payload["total"]),
        affected_one_side=int(payload["affected_one_side"]),
        affected_both_sides=int(payload["affected_both_sides"]),
        examples=_change_examples(payload["examples"]),
    )


def _distance_result_from_json(payload: object) -> DistanceResult:
    if not isinstance(payload, dict):
        raise TypeError("distance results must be mappings")
    return DistanceResult(
        distance_m=float(payload["distance_m"]),
        drawn=int(payload["drawn"]),
        all_borders=_paired_changes_from_json(payload["all_borders"]),
        land_borders=_paired_changes_from_json(payload["land_borders"]),
    )


def _round_to_multiple(values: np.ndarray, quantum: int) -> np.ndarray:
    """Round signed integers to ``quantum``, with ties away from zero."""
    values_i64 = values.astype(np.int64)
    magnitudes = np.abs(values_i64)
    rounded = ((magnitudes + quantum // 2) // quantum) * quantum
    rounded[values_i64 < 0] *= -1
    return rounded


def quantize_ring(ring: np.ndarray, decimal_places: int) -> np.ndarray:
    """Round one stored ring to a coarser decimal grid without dropping vertices.

    The first rounding to six decimal places recovers the source value from the known
    ``coord2int`` artifact: a source integer such as ``133580000`` can be stored as
    ``133579999`` after binary floating-point multiplication and truncation.  Rounding
    that artifact directly to five places would mishandle source values exactly halfway
    between two five-place grid points.
    """
    if not 0 <= decimal_places <= SOURCE_DECIMAL_PLACES:
        raise ValueError(
            f"decimal_places must be between 0 and {SOURCE_DECIMAL_PLACES}, "
            f"got {decimal_places}"
        )
    source_quantum = 10 ** (DECIMAL_PLACES_SHIFT - SOURCE_DECIMAL_PLACES)
    target_quantum = 10 ** (DECIMAL_PLACES_SHIFT - decimal_places)
    source_aligned = _round_to_multiple(ring, source_quantum)
    quantized = _round_to_multiple(source_aligned, target_quantum)
    return np.asarray(quantized, dtype="<i4", order="C")


def _hole_owners(finder: TimezoneFinder) -> list[int]:
    owners = [-1] * finder.nr_of_holes
    for polygon_id, (amount, first_hole_id) in finder.hole_registry.items():
        for hole_id in range(first_hole_id, first_hole_id + amount):
            owners[hole_id] = polygon_id
    if any(owner < 0 for owner in owners):
        raise ValueError("the packaged hole registry does not own every hole id")
    return owners


def quantized_timezone_data(
    finder: TimezoneFinder, decimal_places: int
) -> TimezoneData:
    """Reconstruct the packaged release as a quantized converter model."""
    polygons = [
        quantize_ring(finder.coords_of(polygon_id), decimal_places)
        for polygon_id in range(finder.nr_of_polygons)
    ]
    holes = [
        quantize_ring(finder.holes.coords_of(hole_id), decimal_places)
        for hole_id in range(finder.nr_of_holes)
    ]
    original_polygons = [
        polygon.astype(np.float64) / COORD2INT_FACTOR for polygon in polygons
    ]
    return TimezoneData.create_validated(
        zones=ZoneCollection(
            names=list(finder.timezone_names),
            poly_zone_ids=finder.zone_ids.copy(),
            dtype_str=zone_id_dtype_to_string(finder.zone_ids.dtype),
        ),
        polygon_store=PolygonCollection(
            polygons=polygons,
            lengths=[polygon.shape[1] for polygon in polygons],
            original_polygons=original_polygons,
        ),
        hole_store=HoleCollection(
            holes=holes,
            lengths=[hole.shape[1] for hole in holes],
            polynrs_of_holes=_hole_owners(finder),
        ),
    )


def build_quantized_data(output_path: Path, decimal_places: int) -> str:
    """Build and validate a complete alternative data directory."""
    if output_path.exists():
        raise FileExistsError(
            f"refusing to replace existing quantized data directory: {output_path}"
        )
    output_path.mkdir(parents=True)
    with TimezoneFinder() as source:
        data_version = source.data_version
        data = quantized_timezone_data(source, decimal_places)
    compile_data_files(data, output_path, data_version)
    compile_shortcuts(output_path, data)
    validate_shortcut_index(output_path)
    return data_version


def count_answer_changes(
    points: Iterable[Sequence[float]],
    source_answer: Callable[[float, float], str | None],
    quantized_answer: Callable[[float, float], str | None],
) -> AnswerChanges:
    total = changed = 0
    examples: list[ChangeExample] = []
    for point in points:
        lng, lat = float(point[0]), float(point[1])
        total += 1
        before = source_answer(lng, lat)
        after = quantized_answer(lng, lat)
        if before == after:
            continue
        changed += 1
        if len(examples) < MAX_EXAMPLES:
            examples.append(ChangeExample(lng, lat, before, after))
    return AnswerChanges(total=total, changed=changed, examples=tuple(examples))


def count_paired_changes(
    pairs: Iterable[CandidatePair],
    source_answer: Callable[[float, float], str | None],
    quantized_answer: Callable[[float, float], str | None],
) -> PairedChanges:
    total = one_side = both_sides = 0
    examples: list[ChangeExample] = []
    for pair in pairs:
        total += 1
        changed_sides = 0
        for candidate in (pair.positive, pair.negative):
            before = source_answer(candidate.lng, candidate.lat)
            after = quantized_answer(candidate.lng, candidate.lat)
            if before == after:
                continue
            changed_sides += 1
            if len(examples) < MAX_EXAMPLES:
                examples.append(
                    ChangeExample(candidate.lng, candidate.lat, before, after)
                )
        if changed_sides == 2:
            both_sides += 1
        elif changed_sides == 1:
            one_side += 1
    return PairedChanges(
        total=total,
        affected_one_side=one_side,
        affected_both_sides=both_sides,
        examples=tuple(examples),
    )


def _borders_a_land_zone(pair: CandidatePair, ocean_ring: np.ndarray) -> bool:
    return any(not ocean_ring[ring_id] for ring_id in pair.rings_at_distance)


def sample_uniform_globe(
    rng: np.random.Generator, count: int
) -> Iterable[tuple[float, float]]:
    """Area-uniform coordinates; drawing latitude uniformly would bias the poles."""
    longitudes = rng.uniform(-180.0, 180.0, count)
    latitudes = np.degrees(np.arcsin(rng.uniform(-1.0, 1.0, count)))
    return zip(longitudes, latitudes)


def measure(
    *,
    decimal_places: int = DEFAULT_DECIMAL_PLACES,
    distances_m: Sequence[float] = DEFAULT_DISTANCES_M,
    pairs: int = DEFAULT_PAIRS,
    uniform_points: int = DEFAULT_UNIFORM_POINTS,
    seed: int = DEFAULT_SEED,
) -> Measurement:
    if decimal_places >= SOURCE_DECIMAL_PLACES:
        raise ValueError(
            "the impact study needs a precision below the source's six decimal places"
        )
    (PROJECT_ROOT / "tmp").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="coordinate-precision-", dir=PROJECT_ROOT / "tmp"
    ) as temporary:
        alternative_path = Path(temporary) / "data"
        data_version = build_quantized_data(alternative_path, decimal_places)

        from tests.auxiliaries import boundaries

        geometry = BorderGeometry(boundaries)
        pair_rng = np.random.default_rng(seed)
        uniform_rng = np.random.default_rng(seed + 1)
        with (
            TimezoneFinder(in_memory=True) as source,
            TimezoneFinder(alternative_path, in_memory=True) as quantized,
        ):
            if source.data_version != quantized.data_version:
                raise ValueError("source and quantized data versions do not match")
            ocean_ring = np.array(
                [
                    is_ocean_timezone(source.zone_name_from_boundary_id(ring_id))
                    for ring_id in range(geometry.ring_count)
                ]
            )

            def source_answer(lng: float, lat: float) -> str | None:
                return source.timezone_at(lng=lng, lat=lat)

            def quantized_answer(lng: float, lat: float) -> str | None:
                return quantized.timezone_at(lng=lng, lat=lat)

            by_distance: list[DistanceResult] = []
            for index, distance_m in enumerate(distances_m, start=1):
                print(
                    f"[{index}/{len(distances_m)}] sampling {pairs:,} paired border "
                    f"locations {distance_m:g} m from the source border...",
                    file=sys.stderr,
                    flush=True,
                )
                accepted, drawn = geometry.sample_pairs(pair_rng, distance_m, pairs)
                land_pairs = [
                    pair for pair in accepted if _borders_a_land_zone(pair, ocean_ring)
                ]
                by_distance.append(
                    DistanceResult(
                        distance_m=distance_m,
                        drawn=drawn,
                        all_borders=count_paired_changes(
                            accepted, source_answer, quantized_answer
                        ),
                        land_borders=count_paired_changes(
                            land_pairs, source_answer, quantized_answer
                        ),
                    )
                )

            uniform_globe = count_answer_changes(
                sample_uniform_globe(uniform_rng, uniform_points),
                source_answer,
                quantized_answer,
            )
            by_point_class = {
                name: count_answer_changes(
                    load_benchmark_points(name), source_answer, quantized_answer
                )
                for name in POINT_CLASSES
            }

    return Measurement(
        data_version=data_version,
        source_decimal_places=SOURCE_DECIMAL_PLACES,
        tested_decimal_places=decimal_places,
        quantization="nearest, ties away from zero",
        seed=seed,
        by_distance=tuple(by_distance),
        uniform_globe=uniform_globe,
        by_point_class=by_point_class,
    )


def _format_rate(changes: PairedChanges | AnswerChanges) -> str:
    count = changes.affected if isinstance(changes, PairedChanges) else changes.changed
    if count:
        rate = (
            changes.affected_rate
            if isinstance(changes, PairedChanges)
            else changes.changed_rate
        )
        decimals = 1 if rate >= 1.0 else 2 if rate >= 0.1 else 3
        return f"{count:,} ({rate:.{decimals}f}%)"
    upper_bound = 300.0 / changes.total if changes.total else 0.0
    return f"0 (95% bound <{upper_bound:.3f}%)"


def _format_distance(distance_m: float) -> str:
    return f"{distance_m:g} m" if distance_m >= 1.0 else f"{distance_m * 100:g} cm"


def render_report(measurement: Measurement) -> str:
    """Render the committed RST page from one machine-readable run."""
    any_change = any(result.all_borders.affected for result in measurement.by_distance)
    conclusion = (
        "The source's six decimal places are load-bearing at timezone borders."
        if any_change
        else "This run did not resolve an effect from dropping one decimal place."
    )
    lines = [
        "===========================",
        "Coordinate precision impact",
        "===========================",
        "",
        conclusion,
        "",
        "timezone-boundary-builder publishes six decimal places (~11 cm at the equator).",
        "The packaged int32 representation keeps one redundant decimal so those source",
        "values survive conversion. This study asks the first genuinely lossy question:",
        f"what happens at {measurement.tested_decimal_places} decimal places, using",
        "round-to-nearest so the coarser candidate gets its smallest possible displacement?",
        "",
        "Method",
        "======",
        "",
        f"Boundary release ``{measurement.data_version}`` is used on both sides. The",
        "packaged polygon and hole rings are rounded without removing vertices, then every",
        "binary is regenerated and the H3 shortcut index is rebuilt from that geometry.",
        "Comparing against the old shortcut index would be invalid because its candidate",
        "lists describe the source geometry.",
        "",
        "The border population samples locations uniformly by stored border length and",
        "verifies probes at the stated nearest-border distance on both sides. A location is",
        "affected when either probe changes answer. Ocean-only meridians are reported in the",
        "global column but excluded from the land-zone column. The zero rows are finite-sample",
        "bounds, not claims that the true rate is zero.",
        "",
        ".. list-table:: Paired border locations affected by five-decimal coordinates",
        "   :header-rows: 1",
        "   :widths: 14 18 20 18 20",
        "",
        "   * - Distance",
        "     - Any-border locations",
        "     - Affected",
        "     - Land-border locations",
        "     - Affected",
    ]
    for result in measurement.by_distance:
        lines.extend(
            [
                f"   * - {_format_distance(result.distance_m)}",
                f"     - {result.all_borders.total:,}",
                f"     - {_format_rate(result.all_borders)}",
                f"     - {result.land_borders.total:,}",
                f"     - {_format_rate(result.land_borders)}",
            ]
        )
    decision = (
        [
            "The six-decimal source geometry remains the accuracy floor. Reducing coordinate",
            "precision changes real lookup answers even under nearest rounding, while preserving",
            "it is lossless by construction. A format may omit the package's redundant seventh",
            "decimal, but it must not quantize below the source's six decimals.",
        ]
        if any_change
        else [
            "This finite run found no changed answer, so it cannot justify spending source",
            "precision. The six-decimal source geometry remains the accuracy floor unless a",
            "measurement with enough power establishes a safe coarser alternative.",
        ]
    )
    lines.extend(
        [
            "",
            "Workload-shaped checks",
            "======================",
            "",
            "The same rebuilt data is compared over an area-uniform globe sample and every",
            "committed benchmark point class. These are deliberately reported beside, not in",
            "place of, the border sample: ordinary coordinates are almost never close enough to",
            "a boundary to reveal a sub-metre displacement.",
            "",
            ".. list-table:: Answers changed outside the targeted border population",
            "   :header-rows: 1",
            "   :widths: 45 20 35",
            "",
            "   * - Population",
            "     - Queries",
            "     - Changed answers",
            "   * - Area-uniform globe",
            f"     - {measurement.uniform_globe.total:,}",
            f"     - {_format_rate(measurement.uniform_globe)}",
        ]
    )
    ordered_names = [
        name for name in POINT_CLASSES if name in measurement.by_point_class
    ]
    ordered_names.extend(
        sorted(set(measurement.by_point_class).difference(ordered_names))
    )
    for name in ordered_names:
        changes = measurement.by_point_class[name]
        lines.extend(
            [
                f"   * - ``{name}``",
                f"     - {changes.total:,}",
                f"     - {_format_rate(changes)}",
            ]
        )
    lines.extend(
        [
            "",
            "Decision",
            "========",
            "",
            *decision,
            "",
            "This is a measurement and recommendation, not a data-format change. The packaged",
            "runtime data remains untouched.",
            "",
            f":download:`Machine-readable run <{MEASUREMENT_PATH.name}>`",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--decimal-places", type=int, default=DEFAULT_DECIMAL_PLACES)
    parser.add_argument(
        "--distances",
        type=float,
        nargs="+",
        default=list(DEFAULT_DISTANCES_M),
        metavar="METRES",
    )
    parser.add_argument("--pairs", type=int, default=DEFAULT_PAIRS)
    parser.add_argument("--uniform-points", type=int, default=DEFAULT_UNIFORM_POINTS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--json-out",
        nargs="?",
        const=str(MEASUREMENT_PATH),
        metavar="PATH",
        help=f"save the run (default: {MEASUREMENT_PATH})",
    )
    parser.add_argument(
        "--report-out",
        nargs="?",
        const=str(REPORT_PATH),
        metavar="PATH",
        help=f"write the rendered RST report (default: {REPORT_PATH})",
    )
    parser.add_argument(
        "--from-json",
        nargs="?",
        const=str(MEASUREMENT_PATH),
        metavar="PATH",
        help="render a saved run instead of rebuilding and measuring",
    )
    args = parser.parse_args(argv)

    measurement = (
        Measurement.from_json(json.loads(Path(args.from_json).read_text("utf-8")))
        if args.from_json
        else measure(
            decimal_places=args.decimal_places,
            distances_m=args.distances,
            pairs=args.pairs,
            uniform_points=args.uniform_points,
            seed=args.seed,
        )
    )
    if args.json_out:
        destination = Path(args.json_out)
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_json(measurement.as_json(), destination)
    report = render_report(measurement)
    if args.report_out:
        destination = Path(args.report_out)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(report, encoding="utf-8")
        print(f"wrote {destination}", file=sys.stderr)
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
