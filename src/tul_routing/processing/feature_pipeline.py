from typing import Dict

import numpy as np
import pandas as pd

from ..config import Config
from ..constants import MAP_MATCH_CONFIDENCE, NODE_COLUMN_NAMES
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

    def handle_custom_markers(df, markers: pd.DataFrame):
        if markers is not None:
            for i, m in markers.iterrows():
                df['dist'] = df[['latitude', 'longitude']].apply(
                    lambda p: np.sqrt((p.latitude - m.latitude) ** 2 + (p.longitude - m.longitude) ** 2)
                ,axis=1)
                min_dist = df['dist'].idxmin()
                df.loc[min_dist, m.column] = m.value
        return df

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

        # 6) add way related data based on way_id
        ou.add_way_data,

        # dbg)
        GraphChain(
            handle_custom_markers,
            inputs=lambda x, s: (x, options.get("markers", None))
        ),

        # 7) add node related data based on node_id
        GraphChain(
            ou.label_junctions, verbose=verbose,
            inputs=lambda x, s: (x, True, verbose)
        ),

        # 8) add elevation data to coordinates
        eu.label_elevation,

        # 9) postprocess categoricals
        postprocess_categorical
    ], verbose=verbose)

    numpy_data = input_df[DFLatLongType.columns()].to_numpy()

    graph.process_options(options)
    result = graph.run(numpy_data)

    return result



def postprocess_categorical(df: DFAPIFeaturesTypeLike) -> DFAPIFeaturesTypeLike:
    # ensure columns
    # TODO: ensure we have all the columns
    df = ensure_columns(df, ['node:direction'] + NODE_COLUMN_NAMES, default=np.nan)

    # redukce počtu kategorických proměnných
    # převede hodnoty klíčů, které mají z pohledu modifikace rychlosti stejný význam na stejnou hodnotu
    # odstraní hodnoty klíčů, které nemodifikují rychlost
    # volání funkce je volitelné a jedná se o experimentální postup, jehož efektivitu je 
    # stále nutné otestovat

    # pedestrian_signals není povolená hodnota podle OSM, předpokládám, že je to totéž co traffic_signals
    df.loc[df['node:crossing'] == 'pedestrian_signals', 'node:crossing'] = 'traffic_signals'

    # zebra, marked i unmarked jsou uncontrolled
    df.loc[df['node:crossing'] == 'zebra', 'node:crossing'] = 'uncontrolled'
    df.loc[df['node:crossing'] == 'marked', 'node:crossing'] = 'uncontrolled'
    df.loc[df['node:crossing'] == 'unmarked', 'node:crossing'] = 'uncontrolled'

    # crossing no znamená, že se zde nesmí přecházet, nepodstatné => np.nan
    df.loc[df['node:crossing'] == 'no', ['node:crossing', 'node:highway']] = np.nan

    # pokud direction = backward, tak node ovlivňuje rychlost v protisměru => np.nan
    df.loc[(df['node:highway'] == 'traffic_signals') & (df['node:direction'] == 'backward'), ['node:direction', 'node:highway']] = np.nan
    df.loc[df['node:highway'] == 'traffic_signals', 'node:direction'] = np.nan

    # toll_gantry je mýtná brána, která podle pravidel OSM nevyžaduje zastavení nebo zpomalení => np.nan
    df.loc[df['node:highway'] == 'toll_gantry', 'node:highway'] = np.nan

    # give_way # pokud direction = backward, tak node ovlivňuje rychlost v protisměru => np.nan
    df.loc[(df['node:highway'] == 'give_way') & (df['node:direction'] == 'backward'), ['node:direction', 'node:highway']] = np.nan
    df.loc[df['node:highway'] == 'give_way', 'node:direction'] = np.nan

    # stop # pokud direction = backward, tak node ovlivňuje rychlost v protisměru => np.nan
    df.loc[(df['node:highway'] == 'stop') & (df['node:direction'] == 'backward'), ['node:direction', 'node:highway']] = np.nan
    df.loc[df['node:highway'] == 'stop', 'node:direction'] = np.nan

    # milestone neovlivňuje rychlost
    df.loc[df['node:highway'] == 'milestone', 'node:highway'] = np.nan

    # maxspeed obsahuje hodnotu, která by měla být rovná s way_maxspeed => drop
    #df = df.drop(columns=['node:maxspeed'])

    # proposed neovlivňuje rychlost => np.nan
    df.loc[df['node:highway'] == 'proposed', 'node:highway'] = np.nan

    # speed_display # pokud direction = backward, tak node ovlivňuje rychlost v protisměru => np.nan
    df.loc[(df['node:highway'] == 'speed_display') & (df['node:direction'] == 'backward'), ['node:direction', 'node:highway']] = np.nan
    df.loc[df['node:highway'] == 'speed_display', 'node:direction'] = np.nan

    # direction klíč už neobsahuje relevantní informace, protože zbyly pouze hodnoty forward
    df = df.drop(columns=['node:direction'])

    return df
