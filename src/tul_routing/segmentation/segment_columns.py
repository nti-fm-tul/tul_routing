import pandas as pd
import numpy as np
import pyproj
from scipy.interpolate import interp1d
from sklearn import preprocessing
from ..config import Config, SegmentationKind


geodesic = pyproj.Geod(ellps='WGS84')


def segment_columns(df: pd.DataFrame, options: Config) -> pd.DataFrame:
    remaining_columns = list(df.columns)

    # separate all location dependant features into separate location DataFrame
    # so that the index of value corresponds to integer cumulative distance
    df['step_distance'] = get_step_distance(df)
    df['cum_step_distance'] = df.step_distance.cumsum()

    df.cum_step_distance.iat[0] = 0

    drive_len = df.iloc[-1]['cum_step_distance'] # length of drive in meters
    new_dists = np.arange(0, int(drive_len) + 1, 1) # create linspace to interpolate

    # interpolate geometry
    geometry = interpolate_geometry(df[['latitude', 'longitude']].to_numpy())
    latitude = geometry[:, 1]
    longitude = geometry[:, 0]

    new_df = pd.DataFrame({
        'cum_step_distance': new_dists,
        'latitude': latitude,
        'longitude': longitude,
    })

    once_columns = []
    for k, v in options.segmentation_options.items():
        #print(f"segment_columns: {k} -> {v}")

        if v == SegmentationKind.LINEAR:
            new_df[k] = interpolate_new(df, new_dists, k, "linear")
        elif v == SegmentationKind.NEAREST:
            new_df[k] = interpolate_categorical(df, new_dists, k, "nearest")
        elif v == SegmentationKind.ONCE:
            once_columns.append(k)

        remaining_columns.remove(k)

    for name, dtype in df.dtypes.items():
        if name in remaining_columns:
            if dtype == np.float64:
                new_df[name] = interpolate_new(df, new_dists, name, "linear")
            else:
                print(f"Warning column {name} is of type {dtype} does not have a segmentation strategy")

    location_df = df[once_columns + ['cum_step_distance']].copy()
    #location_df = location_df[~location_df.filter(regex='^node:').isna().all(1)]
    location_df['cum_step_distance'] = location_df['cum_step_distance'].round().astype('int')
    location_df = location_df.drop_duplicates(subset=['cum_step_distance'], keep='first') # drop rows with same cum_step_distance, leave first, greedy, may be better handled

    # merge road dependant and location dependant feature DataFrames
    # into single dataframe
    new_df = pd.merge(new_df, location_df, how='left', on='cum_step_distance', validate='one_to_one')
    # and drop cumulative step distance as it is now represented
    # by integer index
    new_df = new_df.drop(columns=['cum_step_distance'])

    return new_df


def interpolate_new(df, new_dists, col_name, method):
    old_dists = df['cum_step_distance'].to_numpy()
    old_data = df[col_name].to_numpy()

    old_dists = old_dists[~np.isnan(old_data)]
    old_data = old_data[~np.isnan(old_data)]

    if len(old_dists) > 0 and len(old_data) > 0:
        f = interp1d(old_dists, old_data, kind=method)
        return f(new_dists)
    return np.repeat(np.nan, len(new_dists))


def interpolate_categorical(df, new_dists, col_name, method):
    """Interpolates categorical features so that the string labels remain."""
    label_encoder = preprocessing.LabelEncoder()
    df[col_name] = label_encoder.fit_transform(df[col_name])
    new_vals = interpolate_new(df, new_dists, col_name, method)
    new_vals = label_encoder.inverse_transform(new_vals.astype('int'))

    return new_vals


def interpolate_geometry(pnts):
    """Interpolates geometry of a given trace.

    Args:
        pnts (np.array): Array of coordinates sequentially. Distance between points can be arbitrary.

    Returns:
        np.array: Array of sequential coordinates, where each coordinate is one meter apart of the previous
        and following point on the original geometry. Because of that, it is not guaranteed, that the distance
        between consequent output coordinates is one meter.
    """
    az_fw, _, dist = geodesic.inv(pnts[:-1, 1], pnts[:-1, 0], pnts[1:, 1], pnts[1:, 0])
    cdist = np.cumsum(dist)
    offset = np.ceil(cdist) - cdist
    offset = np.insert(offset, 0, 0.0)
    npnts = np.floor(dist - offset[:-1]) + 1

    geometry = np.empty((0, 2))
    for i in range(pnts.shape[0] - 1):
        slon, slat, sbackaz = geodesic.fwd(pnts[i, 1], pnts[i, 0], az_fw[i], offset[i])
        sfwaz = sbackaz + 180
        r = geodesic.fwd_intermediate(
            lon1=slon,
            lat1=slat,
            azi1=sfwaz,
            npts=npnts[i],
            del_s=1,
            initial_idx=0
        )

        newpnts = np.concatenate((np.expand_dims(r.lons, axis=1), np.expand_dims(r.lats, axis=1)), axis=1)

        geometry = np.concatenate((geometry, newpnts))

    return geometry


def set_first_last_value(df, col_name):
    col_idx = df.columns.get_loc(col_name)

    first_valid_index = df[col_name].first_valid_index()
    if first_valid_index is not None:
        # set first value to first valid value
        df.iloc[0, col_idx] = df.iloc[first_valid_index, col_idx]

        # set last value to last valid value
        df.iloc[-1, col_idx] = df.iloc[df[col_name].last_valid_index(), col_idx]

    return df


def get_step_distance(df):
    step_distance = geodesic.inv(
        df['longitude'],
        df['latitude'],
        df['longitude'].shift(),
        df['latitude'].shift()
    )[2]

    return step_distance
