from io import BytesIO
from pathlib import Path
from typing import Iterable, Union

import numpy as np

from timezonefinder import utils
from timezonefinder.flatbuf.polygon_utils import (
    get_coordinate_path,
    get_polygon_collection,
    read_polygon_array_from_binary,
)
from timezonefinder.np_binary_helpers import (
    get_xmax_path,
    get_xmin_path,
    get_ymax_path,
    get_ymin_path,
    read_per_polygon_vector,
)


class PolygonArray:
    xmin: np.ndarray
    xmax: np.ndarray
    ymin: np.ndarray
    ymax: np.ndarray

    def _open_binary(self, path2file):
        """Open a binary file, either in memory or as a file handle.

        Args:
            path2file: Path to the binary file

        Returns:
            Either a BytesIO object (if in_memory=True) or a file handle
        """
        if self.in_memory:
            with open(path2file, mode="rb") as fp:
                opened = BytesIO(fp.read())
                opened.seek(0)
        else:
            opened = open(path2file, mode="rb")
        return opened

    def __init__(
        self,
        data_location: Union[str, Path],
        in_memory: bool = False,
    ):
        """
        Initialize the AbstractTimezoneFinder.
        :param bin_file_location: The path to the binary data files to use. If None, uses native package data.
        :param in_memory: Whether to completely read and keep the binary files in memory.
        """
        self.in_memory = in_memory
        self._file_handle = None

        self.data_location: Path = Path(data_location)

        xmin_path = get_xmin_path(self.data_location)
        xmax_path = get_xmax_path(self.data_location)
        ymin_path = get_ymin_path(self.data_location)
        ymax_path = get_ymax_path(self.data_location)

        # read all per polygon vectors directly into memory (no matter the memory mode)
        self.xmin = read_per_polygon_vector(xmin_path)
        self.xmax = read_per_polygon_vector(xmax_path)
        self.ymin = read_per_polygon_vector(ymin_path)
        self.ymax = read_per_polygon_vector(ymax_path)

        coordinate_file_path = get_coordinate_path(self.data_location)
        # NOTE: this will read the file into memory if in_memory is True,
        # otherwise it will open it as a file handle
        self.coord_file, self.coord_buf = utils.load_buffer(
            coordinate_file_path, in_memory=self.in_memory
        )
        self.polygon_collection = get_polygon_collection(self.coord_buf)

    def __del__(self):
        """Clean up resources when the object is destroyed."""
        utils.close_ressources(self.coord_file, self.coord_buf)

    def __len__(self) -> int:
        """
        Get the number of polygons in the collection.
        :return: Number of polygons
        """
        return len(self.xmin)

    def outside_bbox(self, poly_id: int, x: int, y: int) -> bool:
        """
        Check if a point is outside the bounding box of a polygon.

        :param poly_id: Polygon ID
        :param x: X-coordinate of the point
        :param y: Y-coordinate of the point
        :return: True if the point is outside the boundaries, False otherwise
        """
        if x > self.xmax[poly_id]:
            return True
        if x < self.xmin[poly_id]:
            return True
        if y > self.ymax[poly_id]:
            return True
        if y < self.ymin[poly_id]:
            return True
        return False

    def coords_of(self, idx: int) -> np.ndarray:
        return read_polygon_array_from_binary(self.polygon_collection, idx)

    def pip(self, poly_id: int, x: int, y: int) -> bool:
        """
        Point in polygon (PIP) test.

        :param poly_id: Polygon ID
        :param x: X-coordinate of the point
        :param y: Y-coordinate of the point
        :return: True if the point is inside the polygon, False otherwise
        """
        polygon = self.coords_of(poly_id)
        return utils.inside_polygon(x, y, polygon)

    def pip_with_bbox_check(self, poly_id: int, x: int, y: int) -> bool:
        """
        Point in polygon (PIP) test with bounding box check.

        :param poly_id: Polygon ID
        :param x: X-coordinate of the point
        :param y: Y-coordinate of the point
        :return: True if the point is inside the polygon, False otherwise
        """
        if self.outside_bbox(poly_id, x, y):
            return False
        return self.pip(poly_id, x, y)

    def in_any_polygon(self, poly_ids: Iterable[int], x: int, y: int) -> bool:
        """
        Check if a point is inside any of the specified polygons.

        :param poly_ids: An iterable of polygon IDs
        :param x: X-coordinate of the point
        :param y: Y-coordinate of the point
        :return: True if the point is inside any polygon, False otherwise
        """
        for poly_id in poly_ids:
            if self.pip_with_bbox_check(poly_id, x, y):
                return True
        return False
