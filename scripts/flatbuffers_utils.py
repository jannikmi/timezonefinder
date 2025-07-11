# Utility functions for writing polygons/holes as FlatBuffers
import flatbuffers
from scripts import polygon_fb
import numpy as np


def write_polygon_flatbuffer(file_path, coords):
    x_coords, y_coords = coords
    x_coords = np.asarray(x_coords, dtype=np.uint32)
    y_coords = np.asarray(y_coords, dtype=np.uint32)
    builder = flatbuffers.Builder(0)
    # Create FlatBuffers vectors
    polygon_fb.PolygonStartXCoordsVector(builder, len(x_coords))
    for x in reversed(x_coords):
        builder.PrependUint32(x)
    x_vec = builder.EndVector(len(x_coords))
    polygon_fb.PolygonStartYCoordsVector(builder, len(y_coords))
    for y in reversed(y_coords):
        builder.PrependUint32(y)
    y_vec = builder.EndVector(len(y_coords))
    # Build the Polygon object
    polygon_fb.PolygonStart(builder)
    polygon_fb.PolygonAddXCoords(builder, x_vec)
    polygon_fb.PolygonAddYCoords(builder, y_vec)
    poly = polygon_fb.PolygonEnd(builder)
    builder.Finish(poly)
    buf = builder.Output()
    with open(file_path, "wb") as f:
        f.write(buf)


def write_polygon_collection_flatbuffer(file_path, polygons):
    import flatbuffers
    from scripts import polygon_fb
    import numpy as np

    builder = flatbuffers.Builder(0)
    poly_offsets = []
    for poly in polygons:
        x_coords, y_coords = poly
        x_coords = np.asarray(x_coords, dtype=np.uint32)
        y_coords = np.asarray(y_coords, dtype=np.uint32)
        polygon_fb.PolygonStartXCoordsVector(builder, len(x_coords))
        for x in reversed(x_coords):
            builder.PrependUint32(x)
        x_vec = builder.EndVector(len(x_coords))
        polygon_fb.PolygonStartYCoordsVector(builder, len(y_coords))
        for y in reversed(y_coords):
            builder.PrependUint32(y)
        y_vec = builder.EndVector(len(y_coords))
        polygon_fb.PolygonStart(builder)
        polygon_fb.PolygonAddXCoords(builder, x_vec)
        polygon_fb.PolygonAddYCoords(builder, y_vec)
        poly_offset = builder.EndObject()
        poly_offsets.append(poly_offset)
    polygon_fb.PolygonCollectionStartPolygonsVector(builder, len(poly_offsets))
    for po in reversed(poly_offsets):
        builder.PrependUOffsetTRelative(po)
    polys_vec = builder.EndVector(len(poly_offsets))
    polygon_fb.PolygonCollectionStart(builder)
    polygon_fb.PolygonCollectionAddPolygons(builder, polys_vec)
    collection = builder.EndObject()
    builder.Finish(collection)
    buf = builder.Output()
    with open(file_path, "wb") as f:
        f.write(buf)
