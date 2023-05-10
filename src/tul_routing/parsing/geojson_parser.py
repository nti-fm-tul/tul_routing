from pathlib import Path
from typing import Optional, Union

import geojson
import pandas as pd
from geojson import GeoJSON

from ..typing import DFLatLongType
from ..utils.ensure_type import ensure_type
from .abstract_parser import AbstractParser
from .parse_type import ParseType


class GeoJsonParser(AbstractParser):
    _type = ParseType.GEOJSON

    def __init__(self):
        self._geojson: Optional[GeoJSON] = None

    def parse(self, path_like: Union[Path, str]):
        path = ensure_type(path_like, Path)
        self._geojson = geojson.loads(path.read_text())
        return self

    def get_points(self):
        points = []
        for feature in self._geojson.get("features", []):
            geometry = feature.get("geometry", {})
            g_type = geometry.get("type", None)

            # list of points
            if g_type == "LineString":
                for coords in geometry.get("coordinates", []):
                    points += [coords[:2][::-1]]
            # single point
            elif g_type == "Point":
                continue
                # for now, do not add points, it causes issues, where route can jump from one point to the other
                # coords = geometry.get("coordinates", [])
                # points += [coords[:2][::-1]]

        return pd.DataFrame(points, columns=DFLatLongType.columns())
