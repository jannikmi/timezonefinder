from typing import List, Union
from typing_extensions import Literal

from pydantic import AliasPath, BaseModel, Field


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
