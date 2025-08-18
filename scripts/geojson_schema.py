from typing import List
from typing_extensions import Literal

from pydantic import AliasPath, BaseModel, Field


class PolygonGeometry(BaseModel):
    type: Literal["Polygon"]
    coordinates: List[List[List[float]]]


class MultiPolygonGeometry(BaseModel):
    type: Literal["MultiPolygon"]
    coordinates: List[List[List[List[float]]]]


class Feature(BaseModel):
    type: Literal["Feature"]
    tzid: str = Field(..., validation_alias=AliasPath("properties", "tzid"))

    geometry: PolygonGeometry | MultiPolygonGeometry


class GeoJSON(BaseModel):
    type: Literal["FeatureCollection"]
    features: List[Feature]
