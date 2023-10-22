from typing import Dict

import numpy as np
import pandas as pd

from ..config import Config
from ..constants import MAP_MATCH_CONFIDENCE
from ..etl import Graph, GraphChain
from ..typing import (DFAPIFeaturesTypeLike, DFLatLongType,
                      DFStandardisedTypeLike)
from ..utils.ensure_type import ensure_columns
from .matching_utils import OSRMMatchingUtils
from .overpass_utils import OverpassUtils
from .open_elevation_utils import OpenElevationUtils

def query_features_from_apis(
        input_df: DFStandardisedTypeLike,
        verbose=True,
        options: Dict = None) -> DFAPIFeaturesTypeLike:
    """
    Given a DF with latitude, longitude, extract features and returns enriched

    The pipeline is following:

    * query OSRM server: 'snap' points based on osrm driving match against OSM
    * query OVERPASS server: extract info about roads
    * query ELEVATION server: extract elevation

    Parameters
    ----------
    input_df:
    verbose:
    options:
    """
    config: Config = options.get('config', None)
    ou = OverpassUtils(config)
    mu = OSRMMatchingUtils(config)
    eu = OpenElevationUtils(config)

    match_strict_mode = options is not None and options.get("match_strict_mode", False)

    graph = Graph([
        # 1) match input points against OSM
        #   -> store as variable [match]
        GraphChain(
            match=mu.map_match_osrm,
            inputs=lambda x, state: (x, MAP_MATCH_CONFIDENCE, match_strict_mode)
        ),

        # 2) extract unique coordinates, way_ids and speed from OSRM matching
        mu.match_to_dataframe,

        # 3) extract node ids from OSRM matching and bind them to corresponding coordinates in 'points'
        #   -> store as variable [df]
        GraphChain(
            df=ou.bind_nodes,
            inputs=('__prev__', 'match')
        ),

        # 4) extract original coordinates to matched coordinates 'binding table'
        #   -> store as variable [original_data]
        GraphChain(
            original_data=mu.get_binding_table,
            inputs=lambda x, s: (input_df, s['match'])
        ),

        # 5) bind them to the corresponding coordinates in 'points'
        GraphChain(
            mu.bind_original_data,
            inputs=('df', 'original_data')
        ),

        # 6) add elevation data to coordinates
        eu.label_elevation,

        # 7) add way related data based on way_id
        # enrich way data (routes)
        ou.add_way_data,

        # 8) add node related data based on node_id
        # enrich node data (points)
        GraphChain(
            ou.label_junctions, verbose=verbose,
            inputs=lambda x, s: (x, True, verbose)
        ),

        # 9) remove unwanted columns
        GraphChain(
            drop_unwanted_columns,
            inputs=lambda x, s: (x, config)
        ),
    ], verbose=verbose)

    numpy_data = input_df[DFLatLongType.columns()].to_numpy()

    graph.process_options(options)
    result = graph.run(numpy_data)

    return result


def drop_unwanted_columns(df, config: Config):
    if config.drop_unwanted_columns:
        columns_to_drop = [
            'original_latitude',
            'original_longitude',
        ]
        df = df.drop(columns=columns_to_drop, errors='ignore')
    return df
