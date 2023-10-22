import time
import warnings
from io import StringIO

import numpy as np
import pandas as pd
import pyproj
import requests
from geopy.distance import geodesic
from pandas.core.frame import DataFrame

from ..config import Config
from ..logging import logger
from ..typing import Leg, NPLatLong, OSRMMatchResponse
from ..utils.ensure_type import ensure_columns
from ..utils.geo_calculations import map_path_to_distance


class OSRMMatchingException(Exception):
    """Exception related to OSRM"""
    pass


class OSRMMatchingUtils(object):

    def __init__(self, config: Config):
        self.config = config
        self.osrm_api_server = config.osrm_api_server
        self.request_timeout = config.request_timeout
        self.osrm_location_limit = config.osrm_location_limit

    def construct_osrm_url(self, pnts: NPLatLong, try_harder=False) -> str:
        api_url = f"{self.osrm_api_server}/match/v1/driving/"
        pnts = [f'{p[1]:1.6f},{p[0]:1.6f}' for p in pnts]
        pnts_str = ';'.join(pnts)
        params = '?steps=true&geometries=geojson&overview=full&annotations=true&tidy=false&gaps=ignore'
        if try_harder:
            params += '&radiuses=' + ';'.join(['100'] * len(pnts))
        full_url = api_url + pnts_str + params
        return full_url

    def map_match_osrm(self, pnts: NPLatLong, confidence=0.8, strict_mode=False) -> OSRMMatchResponse:
        """
        Calls map matching request on given trace, if points are not
        matched in a single matching or exit code is not ok, raises exception

        Args:
            pnts (numpy array): ordered array of points describing trace

        Returns:
            json: OSRM map matching response
        """

        step = self.osrm_location_limit
        responses = []
        for i in range(0, len(pnts), step):
            small_pnts = pnts[i:i + step]
            responses.append(
                self._map_match_osrm(small_pnts, confidence, strict_mode)
            )

        base = responses[0]
        pieces = len(responses)

        for i in range(1, pieces):
            resp = responses[i]
            # tracepoints:
            #   waypoint_index starts at 0 again
            base['tracepoints'] += resp['tracepoints']

            base['matchings'][0]['legs'] += resp['matchings'][0]['legs']
            base['matchings'][0]['distance'] += resp['matchings'][0]['distance']
            base['matchings'][0]['duration'] += resp['matchings'][0]['duration']
            base['matchings'][0]['weight'] += resp['matchings'][0]['weight']

            base['matchings'][0]['geometry']['coordinates'] += resp['matchings'][0]['geometry']['coordinates']
            base['matchings'][0]['confidence'] += resp['matchings'][0]['confidence']

        base['matchings'][0]['confidence'] /= pieces
        return base

    def _map_match_osrm(self, pnts: NPLatLong, confidence=0.8, strict_mode=False) -> OSRMMatchResponse:
        """
        Calls map matching request on given trace, if points are not
        matched in a single matching or exit code is not ok, raises exception

        Args:
            pnts (numpy array): ordered array of points describing trace

        Returns:
            json: OSRM map matching response
        """
        full_url = self.construct_osrm_url(pnts)
        res = requests.get(full_url, timeout=self.request_timeout)
        res_json: OSRMMatchResponse = res.json()

        if not res_json['code'] == 'Ok':
            logger.warning(f'OSRM matching failed with code {res_json["code"]}, trying harder')
            full_url = self.construct_osrm_url(pnts, try_harder=True)
            res = requests.get(full_url, timeout=self.request_timeout)
            res_json: OSRMMatchResponse = res.json()

        if not res_json['code'] == 'Ok':
            raise Exception(f"Could not match OSRM model: {res_json.get('message', '')}")

        if len(res_json['matchings']) > 1:
            message = f'Map matching found {len(res_json["matchings"])} solutions, using the first one.'
            if strict_mode:
                raise Exception(message)
            else:
                logger.warn(message)

        if res_json['matchings'][0]['confidence'] < confidence:
            message = f'Map matching failed with matching confidence {res_json["matchings"][0]["confidence"]}'
            if strict_mode:
                raise Exception(message)
            else:
                logger.warn(message)

        return res_json

    def filter_matching(self, match_result: OSRMMatchResponse):
        """transforms matching result dropping irrelevant keys
        and duplicate geometry points

        Args:
            match_result (json): result of map_match_osrm call

        Returns:
            steps: array of dicts with steps metadata
            nodes: array of ids of nodes along the trace
            tracepoints: array of dicts with data to bind original and matched
        """
        nodes = []
        steps = []

        for leg in match_result['matchings'][0]['legs']:
            nodes += leg['annotation']['nodes']
            for step in leg['steps']:
                if step['distance'] >= 0.0001:
                    steps.append({
                        'distance': step['distance'],
                        'duration': step['duration'],
                        'geometry': step['geometry']['coordinates'],
                        'intersections': step['intersections'],
                        'name': step['name']
                    })

        nodes = set(nodes)

        for i in range(1, len(steps)):
            steps[i]['geometry'] = steps[i]['geometry'][1:]

        tracepoints = match_result['tracepoints']

        return steps, nodes, tracepoints

    def get_binding_table(self, df: DataFrame, match: OSRMMatchResponse) -> DataFrame:
        """Performs inner join on input dataframe and matched tracepoints. 
        Df and tracepoints have identical length. Df contains original coordinates
        and tracepoints contains snapped coordinates.
        Args:
            df (pandas DataFrame): std drive log
            match (OSRMMatchResponse): list of dicts of snapped points

        Returns:
            df : input DataFrame without unmatched points rows and columns 'matched_latitude', 'matched_longitude' 
            referring to the 'steps' data from matching
        """
        # more input rows can be matched to same

        tracepoints = match['tracepoints']
        in_rows = df.shape[0]
        df['matched_latitude'] = np.nan
        df['matched_longitude'] = np.nan
        df['match_distance'] = np.nan

        for i, tp in enumerate(tracepoints):
            if tp:
                df.iloc[i, df.columns.get_loc(
                    'matched_latitude')] = tp['location'][1]
                df.iloc[i, df.columns.get_loc(
                    'matched_longitude')] = tp['location'][0]
                df.iloc[i, df.columns.get_loc('match_distance')] = tp['distance']

        # drop all rows of input dataframe that have not been matched
        df = df.dropna(subset=['matched_latitude'])

        out_rows = df.shape[0]

        # if more than 2% of points was not matched
        if in_rows != out_rows and (in_rows - out_rows) / in_rows > 0.02:
            pts_count = in_rows - out_rows
            pts_perc = pts_count / in_rows * 100
            warnings.warn(
                f'{pts_count} input points ({pts_perc:.1f}%) have not been matched and will not be included in the output')

        return df

    def process_leg(self, leg: Leg):
        """Transforms data from leg into array of dictionaries where each
        returned waypoint is unique and has way_id and speed_osrm key"""
        points = []
        for i, s in enumerate(leg['steps'][:-1]):
            osrm_speed = 0
            if s['distance'] > 0 and s['duration'] > 0:
                osrm_speed = s['distance'] / s['duration']
            way_id = s['name']
            if i < len(leg['steps'][:-1]) - 1:
                [points.append({
                    'latitude': pnt[1],
                    'longitude': pnt[0],
                    'speed_osrm': osrm_speed,
                    'way_id': way_id
                }) for pnt in s['geometry']['coordinates'][:-1]]

            else:
                [points.append({
                    'latitude': pnt[1],
                    'longitude': pnt[0],
                    'speed_osrm': osrm_speed,
                    'way_id': way_id
                }) for pnt in s['geometry']['coordinates'][:]]

        return points

    def match_to_dataframe(self, match: OSRMMatchResponse) -> DataFrame:
        """Extracts waypoints, speeds based on OSRM and OSM way_id from map-matching response."""
        coords = []
        legs = match['matchings'][0]['legs']
        for l in legs:
            coords += self.process_leg(l)

        # ensures all waypoints are unique
        filtered = [coords[0]]
        for p in coords[1:]:
            if geodesic([p['latitude'], p['longitude']],
                        [filtered[-1]['latitude'], filtered[-1]['longitude']]).meters > 0.0001:
                filtered.append(p)

        df = pd.DataFrame(filtered)
        df = self.filter_speed_osrm(df)

        return df

    def filter_speed_osrm(self, df: DataFrame) -> DataFrame:
        """Filter speed_osrm."""
        win_len = 100

        df_help = pd.DataFrame()
        df_help['speed_osrm'] = df['speed_osrm']
        df_help["dist"] = [0] + map_path_to_distance(df)
        df_help["dist_cum"] = df_help["dist"].cumsum()
        df_help['speed_osrm_new'] = df_help['speed_osrm']
        for i in range(len(df) - 1):
            pos = (df_help["dist_cum"][i] + df_help["dist_cum"][i + 1]) / 2
            ind = (df_help["dist_cum"] >= pos - win_len / 2) & (df_help["dist_cum"] <= pos + win_len / 2)

            x = ind.index[ind]
            if len(x) > 0:
                if x[-1] < len(df) - 1:
                    ind.iat[x[-1] + 1] = True
            else:
                continue

            df_help['speed_osrm_new'].iat[i] = (df_help.loc[ind, "speed_osrm"] * df_help.loc[ind, "dist"]).sum() / \
                                               df_help.loc[ind, "dist"].sum()

        return df

    def bind_original_data(self, df: DataFrame, original_data: DataFrame) -> DataFrame:

        # matched geometry points
        mpnts = df[['latitude', 'longitude']].to_numpy()

        # original geometry matched points
        opnts = original_data[['matched_latitude', 'matched_longitude']].to_numpy()

        # cdists to deal with loops
        mdist = [geodesic(mpnts[i], mpnts[i - 1]).meters for i in range(1, len(mpnts))]
        mdist.insert(0, 0.0)
        mcdist = np.cumsum(mdist)

        odist = [geodesic(opnts[i], opnts[i - 1]).meters for i in range(1, len(opnts))]
        odist.insert(0, 0.0)
        ocdist = np.cumsum(odist)

        # initialize binding columns
        df['original_latitude'] = np.nan
        df['original_longitude'] = np.nan

        for i in range(opnts.shape[0]):
            match_indices = np.where(np.sum(np.abs(mpnts - opnts[i]), axis=1) < 0.0000001)[0]

            if len(match_indices) > 1:
                warnings.warn("More points matched to the same point.")

            # this part deals with loops
            for j in range(match_indices.shape[0]):
                if ocdist[i] == 0.0:
                    cdist_difference = 0.0
                else:
                    cdist_difference = np.abs(mcdist[match_indices[j]] - ocdist[i]) / ocdist[i]

                # if difference is less than 5%, same round
                if cdist_difference < 0.05:

                    # we have different columns in df and original_data
                    #   the rest of the columns will be mapped dynamically based on the original_data
                    df_columns = df.columns.to_list()
                    original_data_columns = original_data.columns.to_list()

                    df_columns.remove('latitude')
                    df_columns.remove('longitude')
                    original_data_columns.remove('latitude')
                    original_data_columns.remove('longitude')

                    to_map_columns = list(set(df_columns) & set(original_data_columns))

                    df.iloc[match_indices[j], [
                        df.columns.get_loc('original_latitude'),
                        df.columns.get_loc('original_longitude'),
                        *df.columns.get_indexer(to_map_columns)
                    ]] = original_data.iloc[i, [
                        original_data.columns.get_loc('latitude'),
                        original_data.columns.get_loc('longitude'),
                        *original_data.columns.get_indexer(to_map_columns)
                    ]]

                    break

        return df

    def get_timestamp(self, df, speed_column_label='target_speed', start=time.time()):
        step_distance = self.get_step_distance(df)
        step_distance[0] = 0
        step_speed = df[speed_column_label].copy().to_numpy() + (np.random.random() * 1e-6)

        # TODO: step speed can be zero, which means zero division, add a almost nothing just to quick fix this
        #  later on, we must deal with this, issue #9
        step_speed = step_speed + (np.random.random() * 1e-6)

        step_speed[0] = 1
        step_timestamp = np.cumsum(step_distance / step_speed) + start
        step_timestamp[0] = start
        step_timestamp = step_timestamp * 1000

        return step_timestamp

    def get_step_distance(self, df):
        geodesic = pyproj.Geod(ellps='WGS84')
        step_distance = geodesic.inv(
            df['longitude'],
            df['latitude'],
            df['longitude'].shift(),
            df['latitude'].shift()
        )[2]

        return step_distance

    def get_speed(self, df: DataFrame, speed_column_label='speed') -> DataFrame:
        if df.timestamp.isnull().all():  # hack, inconsistent data input when kml data input
            df[speed_column_label] = 0
        else:
            step_dur = df.timestamp.diff() / 1000
            step_dur = step_dur.round(0)  # hack, inconsistent sampling frequency problem
            step_dur[step_dur == 0.0] = np.nan  # hack, incosistent sampling frequency problem
            step_dist = self.get_step_distance(df)
            df[speed_column_label] = step_dist / step_dur

        return df
