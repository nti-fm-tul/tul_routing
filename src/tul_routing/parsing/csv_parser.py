import os
from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd
from pandas import DataFrame

from ..logging import logger
from ..typing import DFLatLongType, DFStandardisedTypeLike
from ..utils.ensure_type import (CheckOutcome, check_timestamp_is_valid_dtype,
                                 ensure_type)
from .abstract_parser import AbstractParser
from .parse_type import ParseType


class CsvParser(AbstractParser):
    _type_ = ParseType.CSV

    def __init__(self):
        self._df: Optional[DataFrame] = None

    # --------------- parsing

    def get_points(self):
        if 'nav_latitude' in self._df:
            ndarray = self._df[['nav_latitude', 'nav_longitude']].values

        elif 'latitude' in self._df:
            ndarray = self._df[['latitude', 'longitude']].values

        elif 'original_latitude' in self._df:
            ndarray = self._df[['original_latitude', 'original_longitude']].values

        else:
            raise Exception(f"Unsupported csv format! Found cols: {self._df.columns}")
            
        return pd.DataFrame(ndarray, columns=DFLatLongType.columns())

    def get_standardised_df(self) -> DFStandardisedTypeLike:
        if 'gps_latitude_external' in self._df and pd.to_numeric(self._df.nav_latitude, errors='coerce').dropna().sum() == 0.0:
            return self._df.rename(columns={'gps_latitude_external': 'latitude', 'gps_longitude_external': 'longitude'})
        
        elif 'nav_latitude' in self._df:
            return self._df.rename(columns={'nav_latitude': 'latitude', 'nav_longitude': 'longitude'})

        elif 'latitude' in self._df:
            return self._df

        elif 'original_latitude' in self._df:
            return self._df.rename(columns={'original_latitude': 'latitude', 'original_longitude': 'longitude'})

        else:
            raise Exception(f"Unsupported csv format! Found cols: {self._df.columns}")

    def parse(self, path_like: Union[Path, str]):
        path = ensure_type(path_like, Path)

        if path.is_dir():
            # input is directory
            self._df = __concat_entry_data(path)

        else:
            # input is single csv

            self._df = pd.read_csv(str(path), delimiter=";")

            if len(self._df.columns) == 1:
                self._df = pd.read_csv(str(path), delimiter=",")

        # fix timestamp
        outcome = check_timestamp_is_valid_dtype(self._df)
        if outcome is not CheckOutcome.UNCHANGED:
            logger.debug(f"Timestamp column must have been fixed: {outcome}")

        if 'gps_latitude_external' in self._df:
            self._df = __filter_entry_df(
                self._df, 
                lat_col='gps_latitude_external', 
                lon_col='gps_longitude_external',
                unique_coords=True)

        elif 'nav_latitude' in self._df:
            self._df = __filter_entry_df(
                self._df, 
                lat_col='nav_latitude', 
                lon_col='nav_longitude',
                unique_coords=True)

        return self



def __concat_entry_data(data_dir):
    '''Recursively gets all files of type csv from directory. Files are than loaded as DataFrame and concatenated together.
    If line of input contains invalid data it is skipped.

    Args:
        data_dir (string): path to directory containing csv drive logs

    Returns:
        DataFrame: concatenation of all csv drive logs to a single DataFrame
    '''
    fpths = [os.path.join(dp, f) for dp, _, fns in os.walk(data_dir) for f in fns if f.endswith('.csv')]

    df = pd.concat((pd.read_csv(f, sep=';', error_bad_lines=False, warn_bad_lines=False
        # on_bad_lines='skip' # this is in pandas version 1.3.0 but we use 1.2.2
        # https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
        ) for f in fpths))

    return df



def __remove_stops_with_time_shift(df, stop_len_threshold=60000):
    """Removes all chunks of rows with zero speed up to stop_len_threshold duration.
    Shifts timestamp_unixms value so the first nonzero speed row after stop
    gets the timestamp_unixms value of the formerly first zero speed row."""
    import cv2

    # mark stops
    df['stopped'] = True
    df.loc[df.speed_esp > 0.0, 'stopped'] = False

    # color stops (assign each stop label)
    img = df.stopped.astype('float').to_numpy().astype(np.uint8)
    _, labels, stats, _ = cv2.connectedComponentsWithStats(img)

    df['stop_label'] = labels

    start = stats[:, 1]  # indices of first stop row
    size = stats[:, 3]  # count of stop rows
    label = np.arange(size.shape[0])  # index for labels
    # duration of stops in milliseconds
    duration = __get_stop_durations(df, start, size)

    # shift times
    # every row since the first row of stop onwards gets duration of the stop subtracted
    # from the timestamp_unixms value
    for i in range(1, start.shape[0]):
        if duration[i] < stop_len_threshold:
            df.iloc[start[i]:, df.columns.get_loc('timestamp_unixms')] -= duration[i]

    # remove stop rows from dataframe
    # every row labeled as stop of lenght less than threshold gets removed
    to_cut = []
    for i in range(1, start.shape[0]):
        if duration[i] < stop_len_threshold:
            to_cut.append(label[i])

    df = df[~df.stop_label.isin(to_cut)]

    df.reset_index(inplace=True, drop=True)

    return df

def longest_truth_chunk(fu):
    '''Given bool array returns start index and length of the longest consecutive sequence of ones.'''
    max_len = 0
    max_idx = None
    i = 0
    while i < fu.shape[0]:
        c_idx = i
        c_len = 0
        if fu[i]:
            while i < fu.shape[0] and fu[i]:
                c_len += 1
                i += 1
        else:
            i += 1
        if c_len > max_len:
            max_len = c_len
            max_idx = c_idx

    return max_idx, max_len


def __get_stop_durations(df, start, size):
    """Gets time difference between first zero speed row in a stop 
    and first nonzero speed row after a stop"""
    duration = np.zeros_like(start)
    for i in range(1, start.shape[0]):
        first_zero_time = df.timestamp_unixms.iloc[start[i]]
        if start[i] + size[i] < df.shape[0]:
            first_nonzero_time = df.timestamp_unixms.iloc[start[i] + size[i]]
        else:  # edge stop case
            first_nonzero_time = df.timestamp_unixms.iloc[start[i] + size[i] - 1]
        duration[i] = first_nonzero_time - first_zero_time

    return duration


def __segment_drives(
    df,
    lat_col='nav_latitude',
    lon_col='nav_longitude',
    time_threshold=5000,
    distance_threshold=100,
    min_length=60
):
    '''Segments input DataFrame to separate drives based on criteria provided.

    Args:
        df (DataFrame): Concatenation of drive logs of a single car.
        lat_col (str, optional): Column containing latitude data. Defaults to 'nav_latitude'.
        lon_col (str, optional): Column containing longitude data. Defaults to 'nav_longitude'.
        time_threshold (int, optional): Time difference threshold between two consecutive rows in milliseconds. If the time difference exceeds the threshold, start/end of drive is detected. Defaults to 5000.
        distance_threshold (int, optional): Distance difference threshold between two consecutive rows in meters. If the distance difference exceeds the threshold, end/start of drive is detected. Defaults to 100.
        min_length (int, optional): Minimal length of segmented drive in rows to output. Allows user to drop short drives. Defaults to 60.

    Returns:
        list[DataFrame]: list of segmented drives
    '''
    from geopy.distance import geodesic as gds
    pts = df[[lat_col, lon_col]].to_numpy()
    step_distance = [gds(pts[i], pts[i-1]).meters for i in range(1, len(pts))]
    step_distance.insert(0, 0.0)
    step_distance = pd.Series(step_distance)
    step_duration = df.timestamp_unixms.diff()
    edge = (step_distance > distance_threshold) | (
        step_duration > time_threshold) | (df.engine_gear == 13)

    label = 0
    labels = np.zeros((edge.shape[0],))
    for i, e in enumerate(edge):
        if e:
            label += 1
        labels[i] = label

    labels = labels

    drives = [group for _, group in df.groupby(labels)]

    drives = [d for d in drives if len(d) > min_length]

    return drives

def __filter_entry_df(
        df,
        lat_col='nav_latitude',
        lon_col='nav_longitude',
        unique_coords=True,
        preserve_reverse=False,
        remove_stops=False,
        stop_threshold=60000
):
    '''Filters rows of the input DataFrame based on criteria provided.

    Args:
        df (DataFrame): Concatenation of drive logs of a single car.
        lat_col (str, optional): Column containing latitude data. Defaults to 'nav_latitude'.
        lon_col (str, optional): Column containing longitude data. Defaults to 'nav_longitude'.
        unique_coords (bool, optional): If set to True, only rows with change of coordinates between 
        consecutive rows are kept. The data is sampled faster, than the sampling frequency of GPS module. 
        This may result in nonsensical values. Defaults to True.
        preserve_reverse (bool, optional): If set to True, all rows with reverse gear are considered 
        start/end of drive. Function than returns longest consecutive DataFrame of rows with no reverse. 
        This functionality can be useful when processing single drive Dataframe. Defaults to False.
        remove_stops (bool, optional): If set to True, consecutive rows with zero speed in column 
        speed_esp are considered stops. If stop lasts for more than stop_threshold value, all rows of the
        stop are removed and timestamp of all remaining rows is shifted appropriately. This helps to 
        preserve more data while at the same time can skew features based on time (isNight). Defaults to False.
        stop_threshold (int, optional): _description_. Defaults to 60000.

    Returns:
        DataFrame: filtered dataframe
    '''
    input_rows = df.shape[0]

    # filter invalid speed_esp values
    # cast speed_esp column to numeric
    df.speed_esp = pd.to_numeric(df.speed_esp, errors='coerce')
    # drop all rows with nan speed_esp value
    df.dropna(subset=['speed_esp'], inplace=True)

    # filter invalid coordinates values (zero values and values out of range)
    df[lat_col] = pd.to_numeric(df[lat_col], errors='coerce')
    df[lon_col] = pd.to_numeric(df[lon_col], errors='coerce')
    df.dropna(subset=[lat_col, lon_col], inplace=True)
    df = df[(df[lat_col] != 0.0) & (df[lon_col] != 0.0)]
    df = df[(df[lat_col] <= 90) & (df[lat_col] >= -90)]
    df = df[(df[lon_col] <= 180) & (df[lon_col] >= -180)]

    # filter invalid timestamp values
    df.timestamp_unixms = pd.to_numeric(df.timestamp_unixms, errors='coerce')
    df.dropna(subset=['timestamp_unixms'], inplace=True)
    df.drop_duplicates(subset=['timestamp_unixms'], inplace=True)

    # sort values
    df.sort_values(by=['timestamp_unixms'], inplace=True)
    df.reset_index(inplace=True, drop=True)

    # remove rows with zero speed
    if remove_stops:
        df = __remove_stops_with_time_shift(
            df, stop_len_threshold=stop_threshold)

    # remove rows with no change in coordinates
    if unique_coords:
        moved = (df[lat_col].diff().fillna(1) != 0.0) | (
            df[lon_col].diff().fillna(1) != 0.0)
        df = df[moved]

    # filter out reverse
    df.reset_index(drop=True, inplace=True)
    if not preserve_reverse:
        no_reverse = (df.engine_gear != 13).to_numpy()
        start, length = longest_truth_chunk(no_reverse)
        df = df[start: start+length]

    # truncate speed
    df = df[df.speed_esp > 0.0]
    df = df[df.speed_esp < 250]
    df.reset_index(drop=True, inplace=True)

    output_rows = df.shape[0]

    relative_rows_dropped = (1 - output_rows / input_rows)
    if relative_rows_dropped > 0.05:
        logger.warn(f'{relative_rows_dropped * 100:.2f}% of rows dropped due to invalid values.')

    return df
