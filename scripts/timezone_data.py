from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Iterator
from typing import Any

import h3.api.numpy_int as h3
import numpy as np
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    ValidationError,
    field_validator,
    model_validator,
)

from scripts.configs import (
    DEBUG,
    DEBUG_ZONE_CTR_STOP,
    MIN_HOLE_DEDUP_RATIO,
    CoordinateArray,
    HoleLengthList,
    HoleRegistry,
    LengthList,
    PolygonList,
    PolynrHolesList,
    ZoneIdArray,
    ZONE_ID_DTYPE,
    ZONE_ID_DTYPE_NUMPY_FORMAT,
)
from timezonefinder.configs import zone_id_dtype_to_string
from scripts.helper_classes import Boundaries, GeoJSON, PolygonGeometry, compile_bboxes
from scripts.hex_utils import Hex
from scripts.utils import canonical_ring_key, to_numpy_polygon_repr


def _validate_numpy_polygons(polygons: PolygonList, kind: str) -> None:
    """Ensure polygon arrays follow the expected shape."""

    for poly in polygons:
        if not isinstance(poly, np.ndarray):
            raise TypeError(f"{kind} polygon must be a numpy array")
        if poly.ndim != 2:
            raise ValueError(f"{kind} polygon array must have 2 dimensions")
        if poly.shape[0] != 2:
            raise ValueError(f"{kind} polygon array must have shape (2, N)")


def _validate_non_decreasing(zone_ids: ZoneIdArray) -> None:
    """Zone ids must not decrease: the converter groups polygons by zone, and
    `zone_positions` reads that grouping off as one start index per zone."""
    last_zone_id = -1
    for zone_id in zone_ids:
        zone_int = int(zone_id)
        if zone_int < last_zone_id:
            raise ValueError(
                f"Zone IDs must be in non-decreasing order, found {zone_int} after {last_zone_id}"
            )
        last_zone_id = zone_int


def _validate_lengths(lengths: list[int], kind: str, minimum: int) -> None:
    if any(length == 0 for length in lengths):
        raise ValueError(f"Found a {kind} with no coordinates")
    if any(length < minimum for length in lengths):
        raise ValueError(f"All {kind}s must have at least {minimum} coordinates")


class ZoneCollection(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    names: list[str]
    poly_zone_ids: ZoneIdArray
    dtype_str: str = ZONE_ID_DTYPE_NUMPY_FORMAT

    @model_validator(mode="after")
    def validate_structure(self) -> "ZoneCollection":
        if self.poly_zone_ids.ndim != 1:
            raise ValueError("poly_zone_ids array must be one-dimensional")

        if self.poly_zone_ids.dtype.kind != "u":
            raise ValueError("Zone IDs must use an unsigned integer dtype")

        if not self.names:
            if self.poly_zone_ids.size:
                raise ValueError(
                    "Zone list cannot be empty when polygon zone ids exist"
                )
            return self

        if self.poly_zone_ids.size == 0:
            return self

        max_zone_id = int(self.poly_zone_ids.max())
        expected_max = self.nr_of_zones - 1
        if max_zone_id != expected_max:
            raise ValueError(
                "Maximum zone ID ({}) should equal nr_of_zones - 1 ({})".format(
                    max_zone_id, expected_max
                )
            )

        _validate_non_decreasing(self.poly_zone_ids)
        return self

    @property
    def nr_of_zones(self) -> int:
        return len(self.names)

    @property
    def nr_of_polygons(self) -> int:
        return int(self.poly_zone_ids.size)

    def zone_positions(self) -> list[int]:
        """Index of the first polygon of each zone, plus a trailing polygon count.

        Does not re-check the ordering: `validate_structure` runs at construction
        and `poly_zone_ids` is never written to afterwards, so a collection that
        exists is already ordered.
        """
        positions: list[int] = []
        last_id = -1
        for poly_idx, zone_id in enumerate(self.poly_zone_ids):
            zone_int = int(zone_id)
            if zone_int != last_id:
                positions.append(poly_idx)
                last_id = zone_int
        positions.append(self.nr_of_polygons)
        return positions


class PolygonCollection(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    polygons: PolygonList
    lengths: LengthList
    original_polygons: list[np.ndarray] | None = None
    _boundaries: list[Boundaries] | None = PrivateAttr(default=None)
    _vertex_hex_cache: dict[int, dict[int, set[int]]] = PrivateAttr(
        default_factory=dict
    )

    @field_validator("polygons")
    @classmethod
    def validate_polygon_arrays(cls, value: PolygonList) -> PolygonList:
        _validate_numpy_polygons(value, "boundary")
        return value

    @model_validator(mode="after")
    def validate_lengths(self) -> "PolygonCollection":
        if len(self.polygons) != len(self.lengths):
            raise ValueError(
                f"Polygon count ({len(self.polygons)}) does not match polygon_lengths entries ({len(self.lengths)})"
            )
        if self.original_polygons is not None and len(self.original_polygons) != len(
            self.polygons
        ):
            raise ValueError("original_polygons length must match number of polygons")
        for idx, (poly, length) in enumerate(zip(self.polygons, self.lengths)):
            if poly.shape[1] != length:
                raise ValueError(
                    f"Polygon {idx} length mismatch: length list value {length} != polygon coordinate count {poly.shape[1]}"
                )
        _validate_lengths(self.lengths, "polygon", minimum=3)
        return self

    @property
    def nr_of_polygons(self) -> int:
        return len(self.lengths)

    @property
    def boundaries(self) -> list[Boundaries]:
        if self._boundaries is None:
            self._boundaries = compile_bboxes(self.polygons)
        return self._boundaries

    def polygon_vertex_hexes(self, poly_nr: int, res: int) -> set[int]:
        res_cache = self._vertex_hex_cache.setdefault(res, {})
        try:
            return res_cache[poly_nr]
        except KeyError:
            if self.original_polygons is None:
                # deliberately unchained: the caught KeyError is the cache miss that
                # got us here, not the cause of the missing coordinates
                raise RuntimeError(
                    f"original polygon coordinates missing, "
                    f"cannot compute vertex hexes of polygon {poly_nr} at resolution {res}"
                ) from None
            coords = self.original_polygons[poly_nr]
            vertex_hexes = {h3.latlng_to_cell(lat, lng, res) for lng, lat in coords.T}
            res_cache[poly_nr] = vertex_hexes
            return vertex_hexes


class HoleCollection(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    holes: PolygonList
    lengths: HoleLengthList
    polynrs_of_holes: PolynrHolesList
    _boundaries: list[Boundaries] | None = PrivateAttr(default=None)
    _registry: HoleRegistry | None = PrivateAttr(default=None)
    _poly_refs: list[int] | None = PrivateAttr(default=None)
    _inline_holes: PolygonList | None = PrivateAttr(default=None)

    @field_validator("holes")
    @classmethod
    def validate_hole_arrays(cls, value: PolygonList) -> PolygonList:
        _validate_numpy_polygons(value, "hole")
        return value

    @model_validator(mode="after")
    def validate_lengths(self) -> "HoleCollection":
        if len(self.holes) != len(self.lengths):
            raise ValueError(
                f"Hole count ({len(self.holes)}) does not match hole_lengths entries ({len(self.lengths)})"
            )
        for idx, (hole, length) in enumerate(zip(self.holes, self.lengths)):
            if hole.shape[1] != length:
                raise ValueError(
                    f"Hole {idx} length mismatch: length list value {length} != hole coordinate count {hole.shape[1]}"
                )
        if len(self.polynrs_of_holes) != len(self.holes):
            raise ValueError("polynrs_of_holes length must match number of holes")
        _validate_lengths(self.lengths, "hole", minimum=3)
        return self

    @property
    def nr_of_holes(self) -> int:
        return len(self.lengths)

    @property
    def boundaries(self) -> list[Boundaries]:
        if self._boundaries is None:
            self._boundaries = compile_bboxes(self.holes)
        return self._boundaries

    @property
    def registry(self) -> HoleRegistry:
        if self._registry is not None:
            return self._registry

        registry: HoleRegistry = {}
        for index, poly_id in enumerate(self.polynrs_of_holes):
            try:
                amount_of_holes, first_hole_id = registry[poly_id]
                registry[poly_id] = (amount_of_holes + 1, first_hole_id)
            except KeyError:
                registry[poly_id] = (1, index)

        self._registry = registry
        return registry

    def validate_references(self, polygon_count: int) -> None:
        if not self.polynrs_of_holes:
            return
        max_poly_ref = max(self.polynrs_of_holes)
        if max_poly_ref >= polygon_count:
            raise ValueError(
                f"Hole references polygon {max_poly_ref} but only {polygon_count} polygons exist"
            )
        min_poly_ref = min(self.polynrs_of_holes)
        if min_poly_ref < 0:
            raise ValueError(
                f"Hole polygon references cannot be negative, found {min_poly_ref}"
            )

    def deduplicate(
        self, polygons: "PolygonCollection", poly_zone_ids: ZoneIdArray
    ) -> None:
        """Recognise every hole that is a verbatim copy of a boundary polygon.

        The upstream builder cuts an enclave out of the surrounding zone using exactly
        the ring it also emits as the enclave zone's own boundary polygon, so the two
        are identical vertex for vertex. Such a hole does not have to be stored at all:
        the reference vector records which boundary to read instead, and only the
        remaining rings are written to the hole coordinate file.

        Populates ``poly_refs`` and ``inline_holes``. Idempotent; the results are cached.

        :param polygons: The boundary polygons that holes are matched against
        :param poly_zone_ids: Zone id per boundary polygon, used to assert that a hole
            never resolves to a polygon of the zone it was cut out of
        """
        if self._poly_refs is not None:
            return

        # A hole and its boundary twin agree on bounding box and vertex count, so
        # bucketing on those first leaves only a handful of candidates to compare in
        # full - the canonical key is what decides, the bucket only narrows the search.
        buckets: dict[tuple[float, float, float, float, int], list[int]] = {}
        for poly_id, bounds in enumerate(polygons.boundaries):
            key = (
                bounds.xmin,
                bounds.xmax,
                bounds.ymin,
                bounds.ymax,
                polygons.lengths[poly_id],
            )
            buckets.setdefault(key, []).append(poly_id)

        canonical_cache: dict[int, bytes] = {}

        def boundary_key(poly_id: int) -> bytes:
            try:
                return canonical_cache[poly_id]
            except KeyError:
                key = canonical_ring_key(polygons.polygons[poly_id])
                canonical_cache[poly_id] = key
                return key

        poly_refs: list[int] = []
        inline_holes: PolygonList = []
        nr_matched = 0
        nr_same_zone = 0
        print("matching holes against identical boundary polygons...")
        for hole_id, hole in enumerate(self.holes):
            bounds = self.boundaries[hole_id]
            candidates = buckets.get(
                (
                    bounds.xmin,
                    bounds.xmax,
                    bounds.ymin,
                    bounds.ymax,
                    self.lengths[hole_id],
                ),
                [],
            )
            match: int | None = None
            if candidates:
                hole_key = canonical_ring_key(hole)
                for poly_id in candidates:
                    if boundary_key(poly_id) == hole_key:
                        match = poly_id
                        break

            if match is None:
                # no twin: keep the ring, and address it by its position in the
                # compacted coordinate file
                poly_refs.append(-(len(inline_holes) + 1))
                inline_holes.append(hole)
                continue

            parent_poly = self.polynrs_of_holes[hole_id]
            if poly_zone_ids[match] == poly_zone_ids[parent_poly]:
                # Not an enclave: a zone cut by a hole shaped like one of its own
                # polygons cancels itself out there. Degenerate upstream geometry,
                # reported rather than rejected - the reference is exact whatever the
                # two zones are, so storing it changes nothing about the answer, and
                # failing the build over it would block a data update for a defect
                # that predates this encoding.
                nr_same_zone += 1
            poly_refs.append(match)
            nr_matched += 1

        nr_holes = len(self.holes)
        if nr_holes:
            ratio = nr_matched / nr_holes
            print(
                f"{nr_matched} of {nr_holes} holes ({ratio:.1%}) stored as a reference "
                f"to an identical boundary polygon"
            )
            if nr_same_zone:
                print(
                    f"WARNING: {nr_same_zone} of them duplicate a polygon of their own "
                    f"zone, which describes a zone that cancels itself out there. "
                    f"Check the input data."
                )
            if ratio < MIN_HOLE_DEDUP_RATIO:
                # Reported, not enforced. A low ratio is a perfectly valid outcome for
                # a custom dataset whose holes are not enclaves - the unmatched rings
                # are stored inline and the result is correct, just larger - and this
                # converter is documented for "any other data in this format"
                # (docs/2_use_cases.rst). What the floor actually protects is the
                # *packaged* data, so it is enforced against that and only that, by
                # scripts.data_integrity.validate_hole_dedup_ratio in the test suite.
                print(
                    f"WARNING: only {ratio:.1%} of holes are identical to a boundary "
                    f"polygon, below the {MIN_HOLE_DEDUP_RATIO:.0%} the packaged "
                    f"dataset is expected to reach. Expected for custom data whose "
                    f"holes are not enclaves. If this IS the packaged dataset, the "
                    f"upstream release has stopped emitting enclaves as shared rings "
                    f"and the data is being silently inflated - re-check with "
                    f"prototypes/hole_boundary_redundancy.py."
                )

        self._poly_refs = poly_refs
        self._inline_holes = inline_holes

    @property
    def poly_refs(self) -> list[int]:
        """One entry per hole id: ``>= 0`` a boundary polygon id, ``< 0`` the inline
        ring at index ``-(v + 1)``. Requires :meth:`deduplicate` to have run."""
        if self._poly_refs is None:
            raise RuntimeError("holes have not been matched against boundaries yet")
        return self._poly_refs

    @property
    def inline_holes(self) -> PolygonList:
        """The hole rings that are not a copy of a boundary polygon, in storage order."""
        if self._inline_holes is None:
            raise RuntimeError("holes have not been matched against boundaries yet")
        return self._inline_holes

    def holes_in_poly(self, poly_nr: int) -> Iterator[CoordinateArray]:
        registry = self.registry
        if poly_nr not in registry:
            return

        hole_count, first_hole_index = registry[poly_nr]
        for i in range(first_hole_index, first_hole_index + hole_count):
            yield self.holes[i]


@dataclass
class HexCache:
    cache: dict[int, Hex] = field(default_factory=dict)

    def get(self, hex_id: int, data: "TimezoneData") -> Hex:
        try:
            return self.cache[hex_id]
        except KeyError:
            hex_obj = Hex.from_id(hex_id, data)
            self.cache[hex_id] = hex_obj
            return hex_obj


@dataclass
class ParseAccumulator:
    """The state a GeoJSON parse builds up, passed down the parse as one object.

    Every field is append-only apart from the two counters, and the collections
    below are handed to `ZoneCollection`, `PolygonCollection` and `HoleCollection`
    unchanged once the parse ends. Threading them as separate parameters is what
    this replaces: several were of the same type, so a transposed pair at any of
    the three call sites type-checked and silently wrote into the wrong list.
    """

    all_tz_names: list[str] = field(default_factory=list)
    polygons: PolygonList = field(default_factory=list)
    polygon_lengths: LengthList = field(default_factory=list)
    poly_zone_ids: list[int] = field(default_factory=list)
    polynrs_of_holes: PolynrHolesList = field(default_factory=list)
    holes: PolygonList = field(default_factory=list)
    all_hole_lengths: HoleLengthList = field(default_factory=list)
    original_polygons: list[np.ndarray] = field(default_factory=list)
    # The id the next polygon receives, and how many holes have been seen so far.
    # Both used to be returned and reassigned at every call level.
    poly_id: int = 0
    nr_of_holes: int = 0

    def add_hole(
        self, hole: list[list[tuple[float, float]]], hole_nr: int, tz_name: str
    ) -> None:
        self.nr_of_holes += 1
        print(
            f"\rpolygon {self.poly_id}, zone {tz_name}, hole number {self.nr_of_holes}, {hole_nr + 1} in polygon",
            end="",
            flush=True,
        )
        self.polynrs_of_holes.append(self.poly_id)
        hole_poly = to_numpy_polygon_repr(hole, from_source=True)
        self.holes.append(hole_poly)
        nr_coords = hole_poly.shape[1]
        self.all_hole_lengths.append(nr_coords)

    def add_polygon_with_holes(
        self,
        poly_with_hole: list[list[list[tuple[float, float]]]],
        zone_id: int,
        tz_name: str,
    ) -> None:
        original_boundary_coords = poly_with_hole[0]
        x_coords_orig, y_coords_orig = zip(*original_boundary_coords)
        if (
            len(x_coords_orig) > 3
            and x_coords_orig[0] == x_coords_orig[-1]
            and y_coords_orig[0] == y_coords_orig[-1]
        ):
            x_coords_orig = x_coords_orig[:-1]
            y_coords_orig = y_coords_orig[:-1]
        original_coord_array = np.array(
            [x_coords_orig, y_coords_orig], dtype=np.float64
        )
        self.original_polygons.append(original_coord_array)

        poly = to_numpy_polygon_repr(poly_with_hole.pop(0), from_source=True)
        self.polygons.append(poly)
        x_coords = poly[0]
        self.polygon_lengths.append(len(x_coords))
        self.poly_zone_ids.append(zone_id)

        for hole_nr, hole in enumerate(poly_with_hole):
            self.add_hole(hole, hole_nr, tz_name)

    def add_timezone_feature(self, zone_id: int, timezone: Any) -> None:
        tz_name = timezone.id
        self.all_tz_names.append(tz_name)
        tz_geometry = timezone.geometry
        multipolygon = tz_geometry.coordinates
        if isinstance(tz_geometry, PolygonGeometry):
            multipolygon = [multipolygon]

        for poly_with_hole in multipolygon:
            self.add_polygon_with_holes(poly_with_hole, zone_id, tz_name)
            self.poly_id += 1


class TimezoneData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    zones: ZoneCollection
    polygon_store: PolygonCollection
    hole_store: HoleCollection
    hex_cache: HexCache = Field(default_factory=HexCache, exclude=True)

    @classmethod
    def create_validated(cls, **kwargs) -> "TimezoneData":
        try:
            return cls(**kwargs)
        except ValidationError as e:
            print("Data validation failed:")
            for error in e.errors():
                print(f"  - {error['loc']}: {error['msg']}")
            raise

    @classmethod
    def from_geojson(
        cls, geo_json: GeoJSON, *, zone_id_dtype: np.dtype = ZONE_ID_DTYPE
    ) -> "TimezoneData":
        if not np.issubdtype(zone_id_dtype, np.unsignedinteger):
            raise ValueError(
                f"Zone ID dtype must be unsigned integer, got {zone_id_dtype}"
            )

        acc = ParseAccumulator()
        print("parsing data...\nprocessing holes:")

        for zone_id, timezone in enumerate(geo_json.features):
            acc.add_timezone_feature(zone_id, timezone)

            if DEBUG and zone_id >= DEBUG_ZONE_CTR_STOP:
                break

        print("\n")

        max_zone_id = len(acc.all_tz_names) - 1
        dtype_info = np.iinfo(zone_id_dtype)
        if max_zone_id > dtype_info.max:
            raise ValueError(
                "Zone ID dtype too small: maximum zone ID "
                f"{max_zone_id} exceeds {zone_id_dtype} capacity ({dtype_info.max}). "
                "Use a larger dtype via --zone-id-dtype or the TIMEZONEFINDER_ZONE_ID_DTYPE env var."
            )

        zone_collection = ZoneCollection(
            names=acc.all_tz_names,
            poly_zone_ids=np.array(acc.poly_zone_ids, dtype=zone_id_dtype),
            dtype_str=zone_id_dtype_to_string(zone_id_dtype),
        )
        polygon_collection = PolygonCollection(
            polygons=acc.polygons,
            lengths=acc.polygon_lengths,
            original_polygons=acc.original_polygons,
        )
        hole_collection = HoleCollection(
            holes=acc.holes,
            lengths=acc.all_hole_lengths,
            polynrs_of_holes=acc.polynrs_of_holes,
        )

        return cls.create_validated(
            zones=zone_collection,
            polygon_store=polygon_collection,
            hole_store=hole_collection,
        )

    @classmethod
    def from_path(
        cls, input_path: Path, *, zone_id_dtype: np.dtype = ZONE_ID_DTYPE
    ) -> "TimezoneData":
        print(f"parsing input file: {input_path}\n...\n")
        geo_json = GeoJSON.model_validate_json(input_path.read_text())
        return cls.from_geojson(geo_json, zone_id_dtype=zone_id_dtype)

    @model_validator(mode="after")
    def validate_consistency(self) -> "TimezoneData":
        polygon_count = self.polygon_store.nr_of_polygons
        zone_polygon_count = self.zones.nr_of_polygons
        if polygon_count != zone_polygon_count:
            raise ValueError(
                f"Polygon count ({polygon_count}) must match number of polygon zone IDs ({zone_polygon_count})"
            )

        zone_count = self.zones.nr_of_zones
        if polygon_count < zone_count:
            raise ValueError(
                f"Number of polygons ({polygon_count}) cannot be less than number of zones ({zone_count})"
            )

        self.hole_store.validate_references(polygon_count)
        return self

    @property
    def all_tz_names(self) -> list[str]:
        return self.zones.names

    @property
    def poly_zone_ids(self) -> ZoneIdArray:
        return self.zones.poly_zone_ids

    @property
    def zone_id_dtype_str(self) -> str:
        return self.zones.dtype_str

    @property
    def polygons(self) -> PolygonList:
        return self.polygon_store.polygons

    @property
    def polygon_lengths(self) -> LengthList:
        return self.polygon_store.lengths

    @property
    def holes(self) -> PolygonList:
        return self.hole_store.holes

    @property
    def all_hole_lengths(self) -> HoleLengthList:
        return self.hole_store.lengths

    @property
    def polynrs_of_holes(self) -> PolynrHolesList:
        return self.hole_store.polynrs_of_holes

    @property
    def original_polygons(self) -> list[np.ndarray] | None:
        return self.polygon_store.original_polygons

    @property
    def nr_of_polygons(self) -> int:
        return self.polygon_store.nr_of_polygons

    @property
    def nr_of_zones(self) -> int:
        return self.zones.nr_of_zones

    @property
    def nr_of_holes(self) -> int:
        return self.hole_store.nr_of_holes

    @property
    def poly_boundaries(self) -> list[Boundaries]:
        return self.polygon_store.boundaries

    @property
    def hole_boundaries(self) -> list[Boundaries]:
        return self.hole_store.boundaries

    @property
    def zone_positions(self) -> list[int]:
        print("Computing where zones start and end...")
        positions = self.zones.zone_positions()
        print("...Done.\n")
        return positions

    def get_hex(self, hex_id: int) -> Hex:
        return self.hex_cache.get(hex_id, self)

    def polygon_vertex_hexes(self, poly_nr: int, res: int) -> set[int]:
        return self.polygon_store.polygon_vertex_hexes(poly_nr, res)

    @property
    def hole_poly_refs(self) -> list[int]:
        """Per hole id, the boundary polygon it duplicates or its inline position.

        See :meth:`HoleCollection.deduplicate` for the encoding.
        """
        self.deduplicate_holes()
        return self.hole_store.poly_refs

    @property
    def inline_holes(self) -> PolygonList:
        """The hole rings that have to be stored, i.e. all but the duplicated ones."""
        self.deduplicate_holes()
        return self.hole_store.inline_holes

    def deduplicate_holes(self) -> None:
        """Match holes against identical boundary polygons, once.

        Not done during construction: it walks every boundary polygon that shares a
        bounding box with some hole, which is wasted work for the callers that build a
        ``TimezoneData`` only to compile shortcuts from it.
        """
        self.hole_store.deduplicate(self.polygon_store, self.poly_zone_ids)

    @property
    def hole_registry(self) -> HoleRegistry:
        return self.hole_store.registry

    def holes_in_poly(self, poly_nr: int) -> Iterator[CoordinateArray]:
        yield from self.hole_store.holes_in_poly(poly_nr)
