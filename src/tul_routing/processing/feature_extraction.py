from ..typing import DFStandardisedTypeLike
from geopy.distance import geodesic as gds
import numpy as np
import pandas as pd
import warnings

def drop_nearby_points(df: DFStandardisedTypeLike, threshold: float = 1.0, lat_col='latitude', lon_col='longitude') -> DFStandardisedTypeLike:
    """Drops all points with step distance less than threshold, filters waiting at intersection
    or congestion points that could possibly ruin matching yet contain no relevant information.    
    """
    # some "locations" are zero
    df = df[df['latitude'] != 0]
    df = df[df['longitude'] != 0]

    original_size = df.shape[0]

    # calculate step distance
    pts = df[[lat_col, lon_col]].to_numpy()
    step_distance = [gds(pts[i], pts[i-1]).meters for i in range(1, len(pts))]
    step_distance.insert(0, 0.0)

    mask = np.zeros((len(step_distance), ), dtype=bool)
    mask[0] = True
    mask[-1] = True

    ahead_distance = 0
    for i, std in enumerate(step_distance):
        ahead_distance += std
        if ahead_distance >= threshold:
            ahead_distance = 0
            mask[i] = True
            
    df = df[mask]

    df.reset_index(drop=True, inplace=True)

    # if more than 10 percent of points was dropped, warn user
    final_size = df.shape[0]
    size_diff = original_size - final_size
    percent_dropped = (size_diff / original_size) * 100
    if percent_dropped > 10.0:
        warnings.warn(
            f'{size_diff} ({percent_dropped}%) points dropped due to distance threshold.')

    return df