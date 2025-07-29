from typing import List, Union
from pydantic import BaseModel


class Geometry(BaseModel):
    type: str
    coordinates: Union[list, List[List[float]], List[List[List[float]]]]


class FeatureProperties(BaseModel):
    tzid: str


class Feature(BaseModel):
    type: str
    properties: FeatureProperties
    geometry: Geometry


class GeoJSON(BaseModel):
    type: str
    features: List[Feature]
