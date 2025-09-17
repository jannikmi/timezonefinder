from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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
from scripts.utils import to_numpy_polygon_repr


def _validate_numpy_polygons(polygons: PolygonList, kind: str) -> None:
    """Ensure polygon arrays follow the expected shape."""

    for poly in polygons:
        if not isinstance(poly, np.ndarray):
            raise TypeError(f"{kind} polygon must be a numpy array")
        if poly.ndim != 2:
            raise ValueError(f"{kind} polygon array must have 2 dimensions")
        if poly.shape[0] != 2:
            raise ValueError(f"{kind} polygon array must have shape (2, N)")


def _validate_lengths(lengths: List[int], kind: str, minimum: int) -> None:
    if any(length == 0 for length in lengths):
        raise ValueError(f"Found a {kind} with no coordinates")
    if any(length < minimum for length in lengths):
        raise ValueError(f"All {kind}s must have at least {minimum} coordinates")


class ZoneCollection(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    names: List[str]
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

        min_zone_id = int(self.poly_zone_ids.min())
        if min_zone_id < 0:
            raise ValueError(f"Zone IDs cannot be negative, found {min_zone_id}")

        last_zone_id = -1
        for zone_id in self.poly_zone_ids:
            zone_int = int(zone_id)
            if zone_int < last_zone_id:
                raise ValueError(
                    f"Zone IDs must be in non-decreasing order, found {zone_int} after {last_zone_id}"
                )
            last_zone_id = zone_int
        return self

    @property
    def nr_of_zones(self) -> int:
        return len(self.names)

    @property
    def nr_of_polygons(self) -> int:
        return int(self.poly_zone_ids.size)

    def zone_positions(self) -> List[int]:
        positions: List[int] = []
        last_id = -1
        for poly_idx, zone_id in enumerate(self.poly_zone_ids):
            zone_int = int(zone_id)
            if zone_int != last_id:
                if zone_int < last_id:
                    raise ValueError(
                        f"Zone IDs must be in non-decreasing order, found {zone_int} after {last_id}"
                    )
                positions.append(poly_idx)
                last_id = zone_int
        positions.append(self.nr_of_polygons)
        return positions


class PolygonCollection(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    polygons: PolygonList
    lengths: LengthList
    original_polygons: Optional[List[np.ndarray]] = None
    _boundaries: Optional[List[Boundaries]] = PrivateAttr(default=None)
    _vertex_hex_cache: Dict[int, Dict[int, Set[int]]] = PrivateAttr(
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
    def boundaries(self) -> List[Boundaries]:
        if self._boundaries is None:
            self._boundaries = compile_bboxes(self.polygons)
        return self._boundaries

    def polygon_vertex_hexes(self, poly_nr: int, res: int) -> Set[int]:
        res_cache = self._vertex_hex_cache.setdefault(res, {})
        try:
            return res_cache[poly_nr]
        except KeyError:
            if self.original_polygons is None:
                raise RuntimeError("original polygon coordinates missing")
            coords = self.original_polygons[poly_nr]
            vertex_hexes = {h3.latlng_to_cell(lat, lng, res) for lng, lat in coords.T}
            res_cache[poly_nr] = vertex_hexes
            return vertex_hexes


class HoleCollection(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    holes: PolygonList
    lengths: HoleLengthList
    polynrs_of_holes: PolynrHolesList
    _boundaries: Optional[List[Boundaries]] = PrivateAttr(default=None)
    _registry: Optional[HoleRegistry] = PrivateAttr(default=None)

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
    def boundaries(self) -> List[Boundaries]:
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

    def holes_in_poly(self, poly_nr: int):
        registry = self.registry
        if poly_nr not in registry:
            return

        hole_count, first_hole_index = registry[poly_nr]
        for i in range(first_hole_index, first_hole_index + hole_count):
            yield self.holes[i]


@dataclass
class HexCache:
    cache: Dict[int, Hex] = field(default_factory=dict)

    def get(self, hex_id: int, data: "TimezoneData") -> Hex:
        try:
            return self.cache[hex_id]
        except KeyError:
            hex_obj = Hex.from_id(hex_id, data)
            self.cache[hex_id] = hex_obj
            return hex_obj


class TimezoneData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    zones: ZoneCollection
    polygon_store: PolygonCollection
    hole_store: HoleCollection
    hex_cache: HexCache = Field(default_factory=HexCache, exclude=True)

    @classmethod
    def _process_hole(
        cls,
        hole: List[List[Tuple[float, float]]],
        poly_id: int,
        hole_nr: int,
        nr_of_holes: int,
        tz_name: str,
        polynrs_of_holes: PolynrHolesList,
        holes: PolygonList,
        all_hole_lengths: HoleLengthList,
    ) -> int:
        nr_of_holes += 1
        print(
            f"\rpolygon {poly_id}, zone {tz_name}, hole number {nr_of_holes}, {hole_nr + 1} in polygon",
            end="",
            flush=True,
        )
        polynrs_of_holes.append(poly_id)
        hole_poly = to_numpy_polygon_repr(hole)
        holes.append(hole_poly)
        nr_coords = hole_poly.shape[1]
        all_hole_lengths.append(nr_coords)
        return nr_of_holes

    @classmethod
    def _process_polygon_with_holes(
        cls,
        poly_with_hole: List[List[List[Tuple[float, float]]]],
        zone_id: int,
        tz_name: str,
        poly_id: int,
        polygons: PolygonList,
        polygon_lengths: LengthList,
        poly_zone_ids: List[int],
        nr_of_holes: int,
        polynrs_of_holes: PolynrHolesList,
        holes: PolygonList,
        all_hole_lengths: HoleLengthList,
        original_polygons: List[np.ndarray],
    ) -> int:
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
        original_polygons.append(original_coord_array)

        poly = to_numpy_polygon_repr(poly_with_hole.pop(0))
        polygons.append(poly)
        x_coords = poly[0]
        polygon_lengths.append(len(x_coords))
        poly_zone_ids.append(zone_id)

        for hole_nr, hole in enumerate(poly_with_hole):
            nr_of_holes = cls._process_hole(
                hole,
                poly_id,
                hole_nr,
                nr_of_holes,
                tz_name,
                polynrs_of_holes,
                holes,
                all_hole_lengths,
            )

        return nr_of_holes

    @classmethod
    def _process_timezone_feature(
        cls,
        zone_id: int,
        timezone: Any,
        poly_id: int,
        all_tz_names: List[str],
        polygons: PolygonList,
        polygon_lengths: LengthList,
        poly_zone_ids: List[int],
        nr_of_holes: int,
        polynrs_of_holes: PolynrHolesList,
        holes: PolygonList,
        all_hole_lengths: HoleLengthList,
        original_polygons: List[np.ndarray],
    ) -> Tuple[int, int]:
        tz_name = timezone.id
        all_tz_names.append(tz_name)
        tz_geometry = timezone.geometry
        multipolygon = tz_geometry.coordinates
        if isinstance(tz_geometry, PolygonGeometry):
            multipolygon = [multipolygon]

        for poly_with_hole in multipolygon:
            nr_of_holes = cls._process_polygon_with_holes(
                poly_with_hole,
                zone_id,
                tz_name,
                poly_id,
                polygons,
                polygon_lengths,
                poly_zone_ids,
                nr_of_holes,
                polynrs_of_holes,
                holes,
                all_hole_lengths,
                original_polygons,
            )
            poly_id += 1

        return poly_id, nr_of_holes

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

        all_tz_names: List[str] = []
        polygons: PolygonList = []
        polygon_lengths: LengthList = []
        poly_zone_ids: List[int] = []
        nr_of_holes: int = 0
        polynrs_of_holes: PolynrHolesList = []
        holes: PolygonList = []
        all_hole_lengths: HoleLengthList = []
        original_polygons: List[np.ndarray] = []

        poly_id: int = 0
        print("parsing data...\nprocessing holes:")

        for zone_id, timezone in enumerate(geo_json.features):
            poly_id, nr_of_holes = cls._process_timezone_feature(
                zone_id,
                timezone,
                poly_id,
                all_tz_names,
                polygons,
                polygon_lengths,
                poly_zone_ids,
                nr_of_holes,
                polynrs_of_holes,
                holes,
                all_hole_lengths,
                original_polygons,
            )

            if DEBUG and zone_id >= DEBUG_ZONE_CTR_STOP:
                break

        print("\n")

        max_zone_id = len(all_tz_names) - 1
        dtype_info = np.iinfo(zone_id_dtype)
        if max_zone_id > dtype_info.max:
            raise ValueError(
                "Zone ID dtype too small: maximum zone ID "
                f"{max_zone_id} exceeds {zone_id_dtype} capacity ({dtype_info.max}). "
                "Use a larger dtype via --zone-id-dtype or the TIMEZONEFINDER_ZONE_ID_DTYPE env var."
            )

        zone_collection = ZoneCollection(
            names=all_tz_names,
            poly_zone_ids=np.array(poly_zone_ids, dtype=zone_id_dtype),
            dtype_str=zone_id_dtype_to_string(zone_id_dtype),
        )
        polygon_collection = PolygonCollection(
            polygons=polygons,
            lengths=polygon_lengths,
            original_polygons=original_polygons,
        )
        hole_collection = HoleCollection(
            holes=holes,
            lengths=all_hole_lengths,
            polynrs_of_holes=polynrs_of_holes,
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
    def all_tz_names(self) -> List[str]:
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
    def original_polygons(self) -> Optional[List[np.ndarray]]:
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
    def poly_boundaries(self) -> List[Boundaries]:
        return self.polygon_store.boundaries

    @property
    def hole_boundaries(self) -> List[Boundaries]:
        return self.hole_store.boundaries

    @property
    def zone_positions(self) -> List[int]:
        print("Computing where zones start and end...")
        positions = self.zones.zone_positions()
        print("...Done.\n")
        return positions

    def get_hex(self, hex_id: int) -> Hex:
        return self.hex_cache.get(hex_id, self)

    def polygon_vertex_hexes(self, poly_nr: int, res: int) -> Set[int]:
        return self.polygon_store.polygon_vertex_hexes(poly_nr, res)

    @property
    def hole_registry(self) -> HoleRegistry:
        return self.hole_store.registry

    def holes_in_poly(self, poly_nr: int):
        yield from self.hole_store.holes_in_poly(poly_nr)
