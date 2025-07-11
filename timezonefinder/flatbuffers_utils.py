# Utility functions for reading polygons/holes from FlatBuffers
import numpy as np
from scripts import polygon_fb


def read_polygon_flatbuffer(file_path):
    with open(file_path, "rb") as f:
        buf = f.read()
    poly = polygon_fb.Polygon.GetRootAsPolygon(buf, 0)
    n = poly.XCoordsLength()
    x_coords = np.array([poly.XCoords(i) for i in range(n)], dtype=np.uint32)
    y_coords = np.array([poly.YCoords(i) for i in range(n)], dtype=np.uint32)
    return np.stack([x_coords, y_coords])


def read_polygon_collection_flatbuffer(file_path):
    with open(file_path, "rb") as f:
        buf = f.read()
    collection = polygon_fb.PolygonCollection.GetRootAsPolygonCollection(buf, 0)
    n = collection.PolygonsLength()

    def get_poly(idx):
        poly = collection.Polygons(idx)
        m = poly.XCoordsLength()
        x_coords = np.array([poly.XCoords(i) for i in range(m)], dtype=np.uint32)
        y_coords = np.array([poly.YCoords(i) for i in range(m)], dtype=np.uint32)
        return np.stack([x_coords, y_coords])

    return n, get_poly
