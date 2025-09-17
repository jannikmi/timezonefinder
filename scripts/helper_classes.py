from typing import List, NamedTuple, Union
import numpy as np

from typing import Literal


from pydantic import (
    AliasPath,
    BaseModel,
    Field,
)

from scripts.configs import PolygonList


class PolygonGeometry(BaseModel):
    """data representation of a timezone geometry consisting of a single polygon with holes"""

    type: Literal["Polygon"]
    # depth: 3
    coordinates: List[List[List[float]]]


class MultiPolygonGeometry(BaseModel):
    """data representation of a timezone geometry consisting of multiple polygons with holes"""

    type: Literal["MultiPolygon"]
    # depth: 4
    coordinates: List[List[List[List[float]]]]


class Timezone(BaseModel):
    """data representation of a timezone"""

    type: Literal["Feature"]
    id: str = Field(..., validation_alias=AliasPath("properties", "tzid"))
    geometry: Union[PolygonGeometry, MultiPolygonGeometry]


class GeoJSON(BaseModel):
    """schema for a timezone dataset in GeoJSON format"""

    type: Literal["FeatureCollection"]
    features: List[Timezone]


class Boundaries(NamedTuple):
    xmax: float
    xmin: float
    ymax: float
    ymin: float

    def overlaps(self, other: "Boundaries") -> bool:
        if not isinstance(other, Boundaries):
            raise TypeError
        if self.xmin > other.xmax:
            return False
        if self.xmax < other.xmin:
            return False
        if self.ymin > other.ymax:
            return False
        if self.ymax < other.ymin:
            return False
        return True


def compile_bboxes(coord_list: PolygonList) -> List[Boundaries]:
    # print("compiling the bounding boxes of the polygons from the coordinates...")
    boundaries: List[Boundaries] = []
    for coords in coord_list:
        x_coords, y_coords = coords
        y_coords = coords[1]
        bounds = Boundaries(
            np.max(x_coords), np.min(x_coords), np.max(y_coords), np.min(y_coords)
        )
        boundaries.append(bounds)
    return boundaries
