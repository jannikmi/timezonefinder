from collections.abc import Iterable
from pathlib import Path
from scripts.configs import (
    DEBUG,
    DEBUG_ZONE_CTR_STOP,
    DTYPE_FORMAT_H_NUMPY,
    HoleLengthList,
    HoleRegistry,
    LengthList,
    PolygonList,
    PolynrHolesList,
    ZoneIdArray,
)
from scripts.helper_classes import Boundaries, GeoJSON, PolygonGeometry, compile_bboxes
from scripts.hex_utils import Hex
from scripts.utils import to_numpy_polygon_repr


import numpy as np
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


from typing import Any, List, Optional, Tuple


class TimezoneData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    all_tz_names: List[str]
    poly_zone_ids: ZoneIdArray
    polygons: PolygonList
    polygon_lengths: LengthList
    nr_of_holes: int
    polynrs_of_holes: PolynrHolesList
    holes: PolygonList
    all_hole_lengths: HoleLengthList

    # Instance-based hex cache to avoid hashability issues
    hex_cache: dict = Field(default_factory=dict, exclude=True)
    # Cache for hole_registry to avoid recomputing
    hole_registry_cached: HoleRegistry = Field(default_factory=dict, exclude=True)
    # Cache for polygon boundaries to avoid expensive recomputation
    poly_boundaries_cached: Optional[List[Boundaries]] = Field(
        default=None, exclude=True
    )
    # Cache for hole boundaries to avoid expensive recomputation
    hole_boundaries_cached: Optional[List[Boundaries]] = Field(
        default=None, exclude=True
    )

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
        """Process a single hole within a polygon.

        Args:
            hole: Hole coordinates
            poly_id: ID of the parent polygon
            hole_nr: Hole number within the polygon (0-based)
            nr_of_holes: Current total number of holes processed
            tz_name: Timezone name for logging
            polynrs_of_holes: List to append polygon IDs that have holes
            holes: List to append processed hole polygons
            all_hole_lengths: List to append hole coordinate counts

        Returns:
            Updated number of holes processed
        """
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
    ) -> int:
        """Process a polygon and all its holes.

        Args:
            poly_with_hole: List containing boundary polygon and holes
            zone_id: Timezone zone ID
            tz_name: Timezone name
            poly_id: Polygon ID
            polygons: List to append processed polygons
            polygon_lengths: List to append polygon coordinate counts
            poly_zone_ids: List to append zone IDs for each polygon
            nr_of_holes: Current number of holes processed
            polynrs_of_holes: List to append polygon IDs that have holes
            holes: List to append processed hole polygons
            all_hole_lengths: List to append hole coordinate counts

        Returns:
            Updated number of holes processed
        """
        # the first entry is the boundary polygon
        # NOTE: starting from here, only coordinates converted into int32 will be considered!
        # this allows using the Numba JIT util functions already here
        poly = to_numpy_polygon_repr(poly_with_hole.pop(0))
        polygons.append(poly)
        x_coords = poly[0]
        polygon_lengths.append(len(x_coords))
        poly_zone_ids.append(zone_id)

        # everything else is interpreted as a hole!
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
        timezone: Any,  # GeoJSON Feature type
        poly_id: int,
        all_tz_names: List[str],
        polygons: PolygonList,
        polygon_lengths: LengthList,
        poly_zone_ids: List[int],
        nr_of_holes: int,
        polynrs_of_holes: PolynrHolesList,
        holes: PolygonList,
        all_hole_lengths: HoleLengthList,
    ) -> Tuple[int, int]:
        """Process a single timezone feature with all its polygons and holes.

        Args:
            zone_id: Timezone zone ID
            timezone: Timezone feature from GeoJSON
            poly_id: Current polygon ID counter
            all_tz_names: List to append timezone names
            polygons: List to append processed polygons
            polygon_lengths: List to append polygon coordinate counts
            poly_zone_ids: List to append zone IDs for each polygon
            nr_of_holes: Current number of holes processed
            polynrs_of_holes: List to append polygon IDs that have holes
            holes: List to append processed hole polygons
            all_hole_lengths: List to append hole coordinate counts

        Returns:
            Tuple of (updated poly_id, updated nr_of_holes)
        """
        tz_name = timezone.id
        all_tz_names.append(tz_name)
        tz_geometry = timezone.geometry
        multipolygon = tz_geometry.coordinates
        # case: MultiPolygon -> depth is 4
        if isinstance(tz_geometry, PolygonGeometry):
            # depth is 3 (only one polygon, possibly with holes!)
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
            )
            poly_id += 1

        return poly_id, nr_of_holes

    @classmethod
    def create_validated(cls, **kwargs) -> "TimezoneData":
        """Create a TimezoneData instance with proper validation error handling.

        Args:
            **kwargs: Keyword arguments for TimezoneData creation

        Returns:
            TimezoneData instance

        Raises:
            ValidationError: If data validation fails with detailed error information
        """
        try:
            return cls(**kwargs)
        except ValidationError as e:
            print("Data validation failed:")
            for error in e.errors():
                print(f"  - {error['loc']}: {error['msg']}")
            raise

    @classmethod
    def from_geojson(cls, geo_json: GeoJSON) -> "TimezoneData":
        """Parse GeoJSON timezone data into TimezoneData model.

        Args:
            geo_json: Parsed GeoJSON timezone data

        Returns:
            TimezoneData instance with processed polygon and hole data
        """
        # Initialize data containers
        all_tz_names: List[str] = []
        polygons: PolygonList = []
        polygon_lengths: LengthList = []
        poly_zone_ids: List[int] = []
        nr_of_holes: int = 0
        polynrs_of_holes: PolynrHolesList = []
        holes: PolygonList = []
        all_hole_lengths: HoleLengthList = []

        poly_id: int = 0
        print("parsing data...\nprocessing holes:")

        # Process each timezone feature
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
            )

            if DEBUG and zone_id >= DEBUG_ZONE_CTR_STOP:
                break

        print("\n")

        return cls.create_validated(
            all_tz_names=all_tz_names,
            poly_zone_ids=np.array(poly_zone_ids, dtype=DTYPE_FORMAT_H_NUMPY),
            polygons=polygons,
            polygon_lengths=polygon_lengths,
            nr_of_holes=nr_of_holes,
            polynrs_of_holes=polynrs_of_holes,
            holes=holes,
            all_hole_lengths=all_hole_lengths,
        )

    @classmethod
    def from_path(cls, input_path: Path) -> "TimezoneData":
        """Parse the timezone data from the input JSON file."""
        print(f"parsing input file: {input_path}\n...\n")
        geo_json = GeoJSON.model_validate_json(input_path.read_text())
        return cls.from_geojson(geo_json)

    @field_validator("polygons", "holes")
    @classmethod
    def check_polygon_shapes(cls, v: PolygonList) -> PolygonList:
        for poly in v:
            if not isinstance(poly, np.ndarray):
                raise TypeError("Polygon must be a numpy array")
            if poly.ndim != 2:
                raise ValueError("Polygon array must have 2 dimensions")
            if poly.shape[0] != 2:
                raise ValueError("Polygon array must have shape (2, N)")
        return v

    def _validate_count_consistency(self, count: int, data_list: List[Any]) -> None:
        """Validate that a count field matches the length of its corresponding list.

        Args:
            count: The count value to validate
            data_list: The list whose length should match the count
        """
        if count != len(data_list):
            raise ValueError(
                f"{count.__name__} ({count}) does not match length of {data_list.__name__} list ({len(data_list)})"
            )

    def _validate_non_negative(self, value: int) -> None:
        """Validate that a value is non-negative.

        Args:
            value: The value to validate
        """
        if value < 0:
            raise ValueError(f"{value.__name__} cannot be negative")

    def _validate_minimum_coordinates(
        self, lengths: LengthList, min_coords: int, item_type: str
    ) -> None:
        """Validate that all items have minimum required coordinates.

        Args:
            lengths: List of coordinate counts
            min_coords: Minimum required coordinates
            item_type: Type of item (e.g., "polygon", "hole") for error messages
        """
        if any(length == 0 for length in lengths):
            raise ValueError(f"Found a {item_type} with no coordinates")

        if any(length < min_coords for length in lengths):
            raise ValueError(
                f"All {item_type}s must have at least {min_coords} coordinates"
            )

    @model_validator(mode="after")
    def validate_basic_counts(self) -> "TimezoneData":
        self._validate_non_negative(self.nr_of_polygons)
        self._validate_non_negative(self.nr_of_zones)
        self._validate_non_negative(self.nr_of_holes)

        if self.nr_of_polygons < self.nr_of_zones:
            raise ValueError(
                f"Number of polygons ({self.nr_of_polygons}) cannot be less than number of zones ({self.nr_of_zones})"
            )
        return self

    @model_validator(mode="after")
    def validate_polygon_data_consistency(self) -> "TimezoneData":
        self._validate_count_consistency(self.nr_of_polygons, self.polygons)
        self._validate_count_consistency(self.nr_of_polygons, self.polygon_lengths)
        self._validate_count_consistency(self.nr_of_polygons, self.poly_boundaries)
        self._validate_count_consistency(self.nr_of_polygons, self.poly_zone_ids)
        return self

    @model_validator(mode="after")
    def validate_zone_data_consistency(self) -> "TimezoneData":
        self._validate_count_consistency(self.nr_of_zones, self.all_tz_names)
        return self

    @model_validator(mode="after")
    def validate_hole_data_consistency(self) -> "TimezoneData":
        self._validate_count_consistency(self.nr_of_holes, self.holes)
        self._validate_count_consistency(self.nr_of_holes, self.all_hole_lengths)
        self._validate_count_consistency(self.nr_of_holes, self.polynrs_of_holes)
        return self

    @model_validator(mode="after")
    def validate_geometric_constraints(self) -> "TimezoneData":
        self._validate_minimum_coordinates(self.polygon_lengths, 3, "polygon")
        self._validate_minimum_coordinates(self.all_hole_lengths, 3, "hole")
        return self

    @model_validator(mode="after")
    def validate_zone_id_constraints(self) -> "TimezoneData":
        if len(self.poly_zone_ids) == 0:
            return self

        max_zone_id = int(max(self.poly_zone_ids))
        if max_zone_id != self.nr_of_zones - 1:
            raise ValueError(
                f"Maximum zone ID ({max_zone_id}) should equal nr_of_zones - 1 ({self.nr_of_zones - 1})"
            )

        min_zone_id = int(min(self.poly_zone_ids))
        if min_zone_id < 0:
            raise ValueError(f"Zone IDs cannot be negative, found {min_zone_id}")

        last_zone_id: int = -1
        for zone_id in self.poly_zone_ids:
            if zone_id < last_zone_id:
                raise ValueError(
                    f"Zone IDs must be in non-decreasing order, found {zone_id} after {last_zone_id}"
                )
            last_zone_id = int(zone_id)
        return self

    @model_validator(mode="after")
    def validate_hole_references(self) -> "TimezoneData":
        if not self.polynrs_of_holes:
            return self

        max_poly_ref: int = max(self.polynrs_of_holes)
        if max_poly_ref >= self.nr_of_polygons:
            raise ValueError(
                f"Hole references polygon {max_poly_ref} but only {self.nr_of_polygons} polygons exist"
            )

        min_poly_ref: int = min(self.polynrs_of_holes)
        if min_poly_ref < 0:
            raise ValueError(
                f"Hole polygon references cannot be negative, found {min_poly_ref}"
            )
        return self

    @property
    def nr_of_polygons(self) -> int:
        """the number of boundary polygons"""
        return len(self.polygon_lengths)

    @property
    def nr_of_zones(self) -> int:
        """the number of timezones"""
        return len(self.all_tz_names)

    @property
    def poly_boundaries(self) -> List[Boundaries]:
        """Compute bounding boxes for polygon boundaries."""
        if self.poly_boundaries_cached is None:
            self.poly_boundaries_cached = compile_bboxes(self.polygons)
        return self.poly_boundaries_cached

    @property
    def hole_boundaries(self) -> List[Boundaries]:
        """Compute bounding boxes for holes."""
        if self.hole_boundaries_cached is None:
            self.hole_boundaries_cached = compile_bboxes(self.holes)
        return self.hole_boundaries_cached

    @property
    def zone_positions(self) -> List[int]:
        """Compute where each timezone starts and ends in the polygon array.

        Returns:
            List of polygon indices where each zone starts, plus one final entry
            indicating where the last zone ends (i.e., total number of polygons).
        """
        poly_nr2zone_id: List[int] = []
        print("Computing where zones start and end...")
        last_id: int = -1
        for poly_nr, zone_id in enumerate(self.poly_zone_ids):
            if zone_id != last_id:
                poly_nr2zone_id.append(poly_nr)
                if zone_id < last_id:
                    raise ValueError(
                        f"Zone IDs must be in non-decreasing order, found {zone_id} after {last_id}"
                    )
                last_id = int(zone_id)

        # ATTENTION: add one more entry for knowing where the last zone ends!
        poly_nr2zone_id.append(self.nr_of_polygons)
        print("...Done.\n")
        return poly_nr2zone_id

    def get_hex(self, hex_id: int) -> Hex:
        """Get a cached Hex instance for the given hex_id.

        This method provides instance-based caching to work around the fact that
        TimezoneData is not hashable and cannot be used with functools.lru_cache.

        Args:
            hex_id: The H3 hexagon ID

        Returns:
            Hex instance for the given hex_id
        """
        if hex_id not in self.hex_cache:
            self.hex_cache[hex_id] = Hex.from_id(hex_id, self)
        return self.hex_cache[hex_id]

    @property
    def hole_registry(self) -> dict:
        """
        Creates a registry mapping each polygon id to a tuple (number of holes, first hole id).

        This property computes the hole registry on-demand from the polynrs_of_holes data
        and caches the result for subsequent calls.
        For each polygon that has holes, it maps: polygon_id -> (amount_of_holes, first_hole_id)

        Returns:
            Dictionary mapping polygon_id -> (amount_of_holes, first_hole_id)
        """
        # Return cached result if already computed
        if self.hole_registry_cached:
            return self.hole_registry_cached

        registry: HoleRegistry = {}
        for i, poly_id in enumerate(self.polynrs_of_holes):
            try:
                amount_of_holes, hole_id = registry[poly_id]
                registry[poly_id] = (amount_of_holes + 1, hole_id)
            except KeyError:
                registry[poly_id] = (1, i)

        # Cache the result for future calls
        self.hole_registry_cached = registry
        return registry

    def holes_in_poly(self, poly_nr: int) -> Optional[Iterable[PolygonList]]:
        registry = self.hole_registry
        if poly_nr not in registry:
            return  # No holes for this polygon

        hole_count, first_hole_index = registry[poly_nr]
        for i in range(first_hole_index, first_hole_index + hole_count):
            yield self.holes[i]
