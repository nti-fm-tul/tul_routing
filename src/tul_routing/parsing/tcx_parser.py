from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd
from pandas import DataFrame
from tcxparser import TCXParser

from ..typing import DFLatLongType
from .abstract_parser import AbstractParser
from .parse_type import ParseType


class TcxParser(AbstractParser):
    _type = ParseType.TCX

    def __init__(self):
        self.tcx_parser: Optional[TCXParser] = None

    def parse(self, path_like: Union[Path, str]) -> AbstractParser:
        with open(path_like, 'r') as fp:
            self.tcx_parser = TCXParser(fp)
        return self

    def get_points(self) -> Union[DataFrame, DFLatLongType]:
        nd_array = np.array(self.tcx_parser.position_values())
        return pd.DataFrame(nd_array, columns=DFLatLongType.columns())