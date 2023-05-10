from pathlib import Path
from typing import List, Tuple, Union

import numpy as np
from pandas import DataFrame, Series

from .df_segmented_type import DFSegmentedType


class DFLatLongType:
    @classmethod
    def columns(cls):
        """
        Returns: column names: ["latitude", "longitude"]

        """
        return [cls.latitude, cls.longitude]

    latitude: Series = "latitude"
    longitude: Series = "longitude"

class DFNavLatLongType:
    @classmethod
    def columns(cls):
        """
        Returns: column names: ["nav_latitude", "nav_longitude"]

        """
        return [cls.nav_latitude, cls.nav_longitude]

    nav_latitude: Series = "nav_latitude"
    nav_longitude: Series = "nav_longitude"

class DFStandardisedType:
    @classmethod
    def columns(cls):
        return [cls.timestamp, cls.latitude, cls.longitude]

    timestamp: Series = "timestamp"
    latitude: Series = "latitude"
    longitude: Series = "longitude"


class DFAPIFeaturesType:
    @classmethod
    def columns(cls):
        return [
            cls.latitude,
            cls.longitude,
            cls.speed_osrm,
            cls.speed_osrm_filtered,
            cls.way_id,
            cls.node_id,
            cls.node_highway,
            cls.node_railway,
            cls.node_crossing,
            cls.original_latitude,
            cls.original_longitude,
            cls.timestamp,
            cls.way_type,
            cls.way_surface,
            cls.n_of_ways,
            cls.elevation
        ]

    latitude: Series = "latitude"
    longitude: Series = "longitude"
    speed_osrm: Series = "speed_osrm"
    speed_osrm_filtered: Series = "speed_osrm_filtered"
    way_id: Series = "way_id"
    node_id: Series = "node_id"
    node_highway: Series = "node:highway"
    node_railway: Series = "node:railway"
    node_crossing: Series = "node:crossing"
    node_direction: Series = "node:direction"
    original_latitude: Series = "original_latitude"
    original_longitude: Series = "original_longitude"
    timestamp: Series = "timestamp"
    way_type: Series = "way_type"
    way_maxspeed: Series = "way_maxspeed"
    way_surface: Series = "way_surface"
    n_of_ways: Series = "n_of_ways"
    elevation: Series = "elevation"
    

DFLatLongTypeLike = Union[DataFrame, DFLatLongType]
NPLatLong = Union[np.ndarray, list]
DFStandardisedTypeLike = Union[DataFrame, DFStandardisedType]
DFAPIFeaturesTypeLike = Union[DataFrame, DFAPIFeaturesType]
DFSegmentedTypeLike = Union[DataFrame, DFSegmentedType]
PointType = Tuple[float, float]
PathLike = Union[Path, str]
RouteType = Union[List[PointType], List[List[float]]]