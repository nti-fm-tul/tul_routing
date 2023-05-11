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
from ..logging import logger
from ..typing import OSRMMatchResponse
from ..utils.timer import Timer, timeit

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

        if 'intersection' not in df:
            df['intersection'] = np.nan

        intersection_indices = df[df.intersection == 'indistinct'].index.to_numpy()
        for i in intersection_indices:
            if i > 0 and i < df.shape[0] - 1:
                df.iloc[i, df.columns.get_loc('intersection')] = self.postprocess_intersection(df, i)

        df = self.fill_in_roundabout_gaps(df)

        return df


    def fill_gap(self, x, v):
        for i in range(0, x.shape[0] - v.shape[0]):
            if np.sum(x[i:i+v.shape[0]] * v) == 2:
                x[i:i+v.shape[0]] = 1
                
        return x


    def fill_in_roundabout_gaps(self, df):
        mask = (df.intersection == 'roundabout').to_numpy().astype('uint8')
        mask = self.fill_gap(mask, np.array([1, 0, 1])) # fill one row gaps
        mask = self.fill_gap(mask, np.array([1, 0, 0, 1])) # fill two row gaps

        df.loc[mask.astype('bool'), 'intersection'] = 'roundabout'

        return df


    def postprocess_intersection(self, df, i):
        """
        Relabels intersections based on way type of ways belonging to the intersection.
        """
        priorities = {
            'motorway': 1,
            'motorway_link': 2,
            'trunk': 3, 
            'trunk_link': 4,
            'primary': 5,
            'primary_link': 6,
            'secondary': 7,
            'secondary_link': 8,
            'tertiary': 9,
            'tertiary_link': 10,
            'residential': 11,
            'living_street': 12,
            'service': 13,
            'unclassified': 14
        }

        df.loc[~df["way_type"].isin(priorities.keys()), "way_type"] = "unclassified"
        
        node_tags = df.iloc[i].way_tags
        all_priorities = set(priorities[w['highway']] for w in node_tags)
        prev_priority = priorities[df.iloc[i-1].way_type]
        next_priority = priorities[df.iloc[i+1].way_type]
        
        if len(all_priorities) == 1:
            return 'indistinct'
        elif prev_priority == next_priority:
            if any((ap < prev_priority for ap in all_priorities)):
                return 'side_to_side'
            else:
                return 'main_to_main'
        elif prev_priority < next_priority:
            return 'main_to_side'
        else:
            return 'side_to_main'


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
        node_dict['node_tags'] = res.nodes[0].tags
        node_dict['way_tags'] = [w.tags for w in res.ways]
        tmp_ways = []

        for w in node_dict['way_tags']:
            if 'junction' in w.keys() and w['junction'] == 'roundabout':
                node_dict['intersection'] = 'roundabout'
                return node_dict

            if len(tmp_ways) == 0:
                tmp_ways.append(w)
                continue

            if 'ref' in w.keys() and w['ref'] in (ws['ref'] for ws in tmp_ways if 'ref' in ws.keys()):
                continue

            if 'name' in w.keys() and w['name'] in (ws['name'] for ws in tmp_ways if 'name' in ws.keys()):
                continue

            tmp_ways.append(w)

        if len(tmp_ways) > 1:
            node_dict['intersection'] = 'indistinct'

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

        node_dict['node_id'] = res.nodes[0].id
        node_dict['i'] = i
        node_dict['node_tags'] = res.nodes[0].tags
        node_dict['way_tags'] = [w.tags for w in res.ways]
        tmp_ways = []

        for w in node_dict['way_tags']:
            if 'junction' in w.keys() and w['junction'] == 'roundabout':
                node_dict['intersection'] = 'roundabout'
                return node_dict
                
            if len(tmp_ways) == 0:
                tmp_ways.append(w)
                continue

            if 'ref' in w.keys() and w['ref'] in (ws['ref'] for ws in tmp_ways if 'ref' in ws.keys()):
                continue

            if 'name' in w.keys() and w['name'] in (ws['name'] for ws in tmp_ways if 'name' in ws.keys()):
                continue

            tmp_ways.append(w)

        if len(tmp_ways) > 1:
            node_dict['intersection'] = 'indistinct'

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
            tags_keys = list(n.tags.keys()) if n.tags else []
            tags_vals = list(n.tags.values()) if n.tags else []

            # handle highway keys
            if 'highway' in tags_keys:
                node_dict['node:highway'] = n.tags['highway']

                if 'crossing' in tags_keys:
                    node_dict['node:crossing'] = n.tags['crossing']
                if 'direction' in tags_keys:
                    node_dict['node:direction'] = n.tags['direction']

            # handle railway keys
            if 'railway' in tags_keys:
                node_dict['node:railway'] = n.tags['railway']

                if 'crossing' in tags_keys:
                    node_dict['node:crossing'] = n.tags['crossing']

            # stop sign
            # traffic_sign=stop, traffic_sign=stop_sign, highway=stop, railway=stop
            if any(x for x in tags_vals if x == 'stop' or x == 'stop_sign'):
                node_dict['node:stop'] = 'stop'
            # stop=yes, stop=all, stop=minor
            elif any(x for x in tags_keys if x == 'stop' or x == 'stop_sign'):
                node_dict['node:stop'] = 'stop'

            node_dicts.append(node_dict)

        node_df = gpd.GeoDataFrame(node_dicts)

        df = df.drop(columns=['node_id', 'node:highway', 'node:crossing', 'node:railway', 'node:direction'])
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
            way_dict = {}
            way_dict['way_id'] = way.id
            way_dict['way_type'] = way.tags['highway'] if 'highway' in way.tags.keys(
            ) else None
            way_dict['way_maxspeed'] = way.tags['maxspeed'] if 'maxspeed' in way.tags.keys(
            ) else None
            way_dict['way_surface'] = way.tags['surface'] if 'surface' in way.tags.keys(
            ) else None
            way_data.append(way_dict)

        way_df = pd.DataFrame(way_data)

        df['way_id'] = df['way_id'].astype('int')
        df = df.drop(columns=['way_type', 'way_maxspeed', 'way_surface'])
        df = pd.merge(df, way_df, how='left', on='way_id', validate='many_to_one')
        # fix
        df = df.astype({'way_maxspeed': 'float64'})

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
