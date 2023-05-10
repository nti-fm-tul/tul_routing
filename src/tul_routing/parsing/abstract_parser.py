import abc

import numpy as np

from ..typing import (DFLatLongTypeLike, DFStandardisedType,
                      DFStandardisedTypeLike, PathLike)


class AbstractParser(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def parse(self, path_like: PathLike) -> 'AbstractParser':
        """
        Parse given path or path-like object and return the parser
        """
        pass

    @abc.abstractmethod
    def get_points(self) -> DFLatLongTypeLike:
        """
        Extract GPS points from the file
        :return: a dataframe with 'latitude' and 'longitude' columns
        """
        pass

    def get_standardised_df(self) -> DFStandardisedTypeLike:
        """
        Extract GPS points from the file
        :return: a dataframe with 'timestamp', 'latitude' and 'longitude' columns
        """
        points = self.get_points()

        if DFStandardisedType.timestamp not in points:
            # # issue #1
            # import time
            # import numpy as np
            # now = int(time.time())
            # times = np.arange(now, now + len(points))
            points[DFStandardisedType.timestamp] = np.nan

        return points[DFStandardisedType.columns()]
