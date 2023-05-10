from pathlib import Path
from typing import List, Optional, Union

import gpxpy
import gpxpy.gpx
import numpy as np
import pandas as pd

from ..typing import DFLatLongType
from ..utils.ensure_type import ensure_type
from .abstract_parser import AbstractParser
from .parse_type import ParseType


class GpxParser(AbstractParser):
    _type = ParseType.GPX

    def __init__(self):
        self._gpx: Optional[gpxpy.gpx.GPX] = None

    def parse(self, path_like: Union[Path, str]):
        path = ensure_type(path_like, Path)
        data = path.read_text()
        self._gpx = gpxpy.parse(data)
        return self

    def get_points(self):
        points = self._get_points_from_tracks()

        if len(points) == 0:
            points = self._get_points_from_waypoints()
        if len(points) == 0:
            points = self._get_points_from_routes()

        return pd.DataFrame(np.array(points), columns=DFLatLongType.columns())

    def _get_points_from_routes(self) -> List[List[float]]:
        """
        uses <rte><rtept /> elements
        :return:
        """
        points = []
        for route in self._gpx.routes:
            for point in route.points:
                points += [[point.latitude, point.longitude]]
        return points

    def _get_points_from_tracks(self) -> List[List[float]]:
        """
        uses <trk><trkseg><trkpt /> elements
        :return:
        """
        points = []
        for track in self._gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    points += [[point.latitude, point.longitude]]
        return points

    def _get_points_from_waypoints(self) -> List[List[float]]:
        """
        Uses <wpt> elements
        :return:
        """
        points = []
        for waypoint in self._gpx.waypoints:
            points += [[waypoint.latitude, waypoint.longitude]]
        return points
