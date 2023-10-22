import concurrent
import concurrent.futures
import functools
from concurrent.futures import as_completed

import geopandas as gpd
import numpy as np
import overpy
import pandas as pd
from pandas.core.frame import DataFrame
from shapely.geometry import Point
from tqdm import tqdm

from ..config import Config
from ..typing import OSRMMatchResponse
from ..utils.timer import Timer


class OverpassUtils:

    def __init__(self, config: Config) -> None:
        self.config = config
        self.overpass_api_server = config.overpass_api_server

    def label_junctions(self, df: DataFrame, parallel=True, verbose=True) -> DataFrame:
        """
        Recursively queries all node ids in dataframe and adds
        column 'n_of_ways' to rows with node_id in dataframe which
        denounces number of ways from node id.

        Parameters
        ----------
        df : DataFrame
        parallel : bool
            if True will run all queries in parallel
        """
        if not parallel:
            return self._label_junctions(df)

        df['node_id'] = df['node_id'].astype('Int64')
        node_ids = list(pd.unique(df['node_id']).dropna())
        node_ids = list(map(str, node_ids))
        node_data = []

        if verbose:
            bar_format = Timer.current_padding() + "label_junctions: {l_bar}{bar} {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
            pbar = tqdm(total=len(node_ids), bar_format=bar_format)

        with concurrent.futures.ThreadPoolExecutor(max_workers=None) as executor:
            futures = [executor.submit(self.load_node_dict_by_node_id, nid, i) for i, nid in enumerate(node_ids)]
            for future in as_completed(futures):
                result = future.result()
                node_data.append(result)
                if verbose:
                    pbar.update(1)

        if verbose:
            pbar.close()

        node_df = pd.DataFrame(node_data)
        node_df = node_df.sort_values(by='i')
        node_df = node_df.drop(columns=['i'])

        df['node_id'] = df['node_id'].fillna(-1)

        df = pd.merge(df, node_df, how='left', on='node_id', validate='many_to_one')

        df.loc[df['node_id'] == -1, 'node_id'] = np.nan

        return df

    def fill_gap(self, x, v):
        for i in range(0, x.shape[0] - v.shape[0]):
            if np.sum(x[i:i + v.shape[0]] * v) == 2:
                x[i:i + v.shape[0]] = 1

        return x

    def _label_junctions(self, df: DataFrame) -> DataFrame:
        """
        Recursively queries all node ids in dataframe and adds
        column 'n_of_ways' to rows with node_id in dataframe which
        denounces number of ways from node id.
        """

        df['node_id'] = df['node_id'].astype('Int64')
        node_ids = list(pd.unique(df['node_id']).dropna())
        node_ids = [str(nid) for nid in node_ids]
        node_data = []

        for nid in node_ids:
            node_dict = {}
            res = self.query_node_ways_by_id(nid)

        node_dict['node_id'] = res.nodes[0].id

        node_data.append(node_dict)

        node_df = pd.DataFrame(node_data)
        df['node_id'] = df['node_id'].fillna(-1)

        df = df.drop(columns=['n_of_ways'])
        df = pd.merge(df, node_df, how='left', on='node_id', validate='many_to_one')
        df['n_of_ways'] = df['n_of_ways'].fillna(1)

        df.loc[df['node_id'] == -1, 'node_id'] = np.nan

        return df

    def load_node_dict_by_node_id(self, nid, i):
        node_dict = dict()
        res = self.query_node_ways_by_id(nid)

        if self.config.enrich_options.node_enrichment:
            new_node_dict = self.config.enrich_options.node_enrichment(res.nodes[0].tags)
            node_dict.update(new_node_dict)

        node_dict['node_id'] = res.nodes[0].id
        node_dict['i'] = i

        return node_dict

    @functools.lru_cache(maxsize=10_000)
    def query_node_ways_by_id(self, node_id):
        api_server = f"{self.overpass_api_server}/api/interpreter"
        api = overpy.Overpass(url=api_server)

        way_types = [
            'motorway',
            'motorway_link',
            'trunk',
            'trunk_link',
            'primary',
            'primary_link',
            'secondary',
            'secondary_link',
            'tertiary',
            'tertiary_link',
            'residential',
            'living_street',
            'service',
            'unclassified'
        ]

        query = (
                '[out:json];'
                'node(id:' + node_id + ');'
                                       'out;'
                                       'way(bn)[highway~"^(' + '|'.join(way_types) + ')$"];'
                                                                                     'out;'
        )

        res = self.overpass_query(api, query)

        return res

    def query_nodes_coords_by_id(self, node_ids):
        api_server = f"{self.overpass_api_server}/api/interpreter"
        api = overpy.Overpass(url=api_server)

        query = (
                '[out:json];'
                'node(id:' + ",".join(node_ids) + ');'
                                                  'out;'
        )
        res = self.overpass_query(api, query)

        return res

    def query_ways_by_id(self, way_ids):
        api_server = f"{self.overpass_api_server}/api/interpreter"
        api = overpy.Overpass(url=api_server)

        query = (
                '[out:json];'
                'way(id:' + ",".join(way_ids) + ');'
                                                'out;'
        )
        res = self.overpass_query(api, query)

        return res

    def bind_nodes(self, df: DataFrame, match: OSRMMatchResponse) -> DataFrame:
        """Queries all node ids and binds them to waypoints according to the spatial proximity.
        Waypoints have limited precision and node ids can not be matched precisely in one to one way."""
        # polohy nesedí přesně kvůli zaokrouhlování na straně OSRM, chyba zaokrouhlování by měla být do 0.5 metru
        # není zaručeno, že jedna trasa neobsahuje stejné uzly (cykly)
        # není zaručeno, že trasa obsahuje všechny uzly vrácené OSRM

        node_ids = []
        for l in match['matchings'][0]['legs']:
            node_ids += l['annotation']['nodes']

        node_ids = set(node_ids)
        node_ids = [str(n) for n in node_ids]

        res = self.query_nodes_coords_by_id(node_ids)

        df = gpd.GeoDataFrame(df)
        df['geometry'] = gpd.GeoSeries(map(Point, df[['longitude', 'latitude']].to_numpy()))
        df['geometry'] = df['geometry'].buffer(1.2e-6)

        # expand tags dictionary
        # vyřazen node:maxspeed, hodnota buď chybí nebo je implicitně závislá na way_maxspeed
        node_dicts = []
        for n in res.nodes:
            node_dict = {'node_id': int(n.id), 'geometry': Point(n.lon, n.lat)}
            node_dicts.append(node_dict)

        node_df = gpd.GeoDataFrame(node_dicts)

        df = df.drop(columns=['node_id', 'node:highway', 'node:crossing', 'node:railway', 'node:direction'], errors='ignore')
        df = gpd.sjoin(df, node_df, how='left', op='contains')

        df = df.drop(columns=['index_right', 'geometry'])

        return df

    def add_way_data(self, df: DataFrame) -> DataFrame:
        """Queries all way ids in dataframe and adds tags describing
        way to each waypoint"""

        way_ids = np.unique(df['way_id'])

        res = self.query_ways_by_id(way_ids)

        way_data = []
        for way in res.ways:

            way_dict = dict()
            if self.config.enrich_options.way_enrichment:
                way_dict = self.config.enrich_options.way_enrichment(way.tags)
            else:
                way_dict['way_type'] = way.tags.get('highway', None)
                way_dict['way_maxspeed'] = way.tags.get('maxspeed', None)
                way_dict['way_surface'] = way.tags.get('surface', None)

            way_dict['way_id'] = way.id
            way_data.append(way_dict)

        way_df = pd.DataFrame(way_data)

        df['way_id'] = df['way_id'].astype('int')

        way_df_cols = list(way_df.columns)
        way_df_cols.remove('way_id')
        df = df.drop(columns=way_df_cols, errors='ignore')

        df = pd.merge(df, way_df, how='left', on='way_id', validate='many_to_one')

        return df

    def overpass_query(self, api: overpy.Overpass, query: str) -> overpy.Result:
        """
        Query the Overpass API with timeout passing support

        :param String|Bytes query: The query string in Overpass QL
        :return: The parsed result
        :rtype: overpy.Result
        """
        from urllib.error import HTTPError
        from urllib.request import urlopen

        from ..config import request_timeout
        from overpy import exception

        if not isinstance(query, bytes):
            query = query.encode("utf-8")

        try:
            f = urlopen(api.url, query, timeout=request_timeout)
        except HTTPError as e:
            f = e

        response = f.read(api.read_chunk_size)
        while True:
            data = f.read(api.read_chunk_size)
            if len(data) == 0:
                break
            response = response + data
        f.close()

        if f.code == 200:
            content_type = f.getheader("Content-Type")

            if content_type == "application/json":
                return api.parse_json(response)

            if content_type == "application/osm3s+xml":
                return api.parse_xml(response)

            raise exception.OverpassUnknownContentType(content_type)

        if f.code == 400:
            msgs = []
            for msg in api._regex_extract_error_msg.finditer(response):
                tmp = api._regex_remove_tag.sub(b"", msg.group("msg"))
                try:
                    tmp = tmp.decode("utf-8")
                except UnicodeDecodeError:
                    tmp = repr(tmp)
                msgs.append(tmp)

            raise exception.OverpassBadRequest(
                query,
                msgs=msgs
            )

        if f.code == 429:
            raise exception.OverpassTooManyRequests

        if f.code == 504:
            raise exception.OverpassGatewayTimeout

        raise exception.OverpassUnknownHTTPStatusCode(f.code)
