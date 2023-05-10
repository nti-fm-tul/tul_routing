import json
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd

from ..typing import DFLatLongTypeLike, PathLike
from ..utils.ensure_type import ensure_type
from .abstract_parser import AbstractParser


class RouteParser(AbstractParser):
    _col_rename = {
        'time': 'timestamp_unixms',
    }

    def __init__(self) -> None:
        super().__init__()
        self.points = []
        self._df: Optional[pd.DataFrame] = None
        
    def parse(self, path_like: PathLike) -> 'AbstractParser':
        """
        Parse given path or path-like object and return the parser
        """
        path = ensure_type(path_like, Path)
        data = json.loads(path.read_text())

        if self._is_list_of_items(data):
            self._df = pd.DataFrame(data)
            self._df.rename(columns=self._col_rename, inplace=True)
            now = int(time.time() * 1000)
            # add now to every row, which has timestamp_unixms not None
            self._df.loc[self._df.timestamp_unixms.notnull(), 'timestamp_unixms'] += now

            return self

        data = self._handle_viroco_json_format(data)
        self._df = pd.DataFrame(data)
        return self

    def get_points(self) -> DFLatLongTypeLike:
        """
        Extract GPS points from the file
        :return: a dataframe with 'latitude' and 'longitude' columns
        """
        return self._df

    @staticmethod
    def _is_list_of_items(data: any):
        return isinstance(data, list) and all(isinstance(item, dict) for item in data)

    @staticmethod
    def _handle_viroco_json_format(old_data: List[dict]):
        from api.models.RouteModel import Point, RouteModel
        from api.processing.routeUtils import (FindRouteOptions,
                                               find_route_segments)

        data = RouteModel.parse_obj(old_data)
        route_options = FindRouteOptions(split_after_every_segment=True)

        # convert to dataframe
        all_points = [] # type: List[Point]
        
        for points, segment_id, subsegment_id in find_route_segments(data, route_options):
            points_as_dict = [x.dict() for x in points]
            all_points.extend(points_as_dict)

        return all_points
