import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import pandas as pd

from ..typing import DFLatLongType
from ..utils.ensure_type import ensure_type
from .abstract_parser import AbstractParser
from .parse_type import ParseType


class KmlParser(AbstractParser):
    _type_ = ParseType.KML

    def __init__(self):
        self._tree: Optional[ET.ElementTree] = None

    # --------------- parsing

    @classmethod
    def _get_coordinate_elements(cls, element: ET.Element):
        xlmns = '{http://www.opengis.net/kml/2.2}'
        for place_mark in element.iter(f'{xlmns}Placemark'):
            coordinates = place_mark.findall(f'{xlmns}LineString/{xlmns}coordinates')
            yield from coordinates

    @classmethod
    def _parse_coordinates(cls, points_strings: List[str]):
        for pnt_str in points_strings:
            # from string
            #   "15.06467,50.76315,0"
            # to float[]
            #   [50.76315, 15.06467]
            yield from [list(map(float, p.strip().split(',')[:2][::-1])) for p in pnt_str.split('\n') if p.strip()]

    def get_points(self):
        root = self._tree.getroot()
        elements = list(self._get_coordinate_elements(root))
        texts = [e.text for e in elements]
        points = list(self._parse_coordinates(texts))
        array = np.array(points)

        return pd.DataFrame(array, columns=DFLatLongType.columns())

    def parse(self, path_like: Union[Path, str]):
        path = ensure_type(path_like, Path)
        self._tree = ET.parse(path)
        return self

