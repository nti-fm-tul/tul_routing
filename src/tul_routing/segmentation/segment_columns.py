import pandas as pd
import numpy as np
from ..config import Config


def segment_columns(df: pd.DataFrame, options: Config) -> pd.DataFrame:
    remaining_columns = list(df.columns)
    for k, v in options.segmentation_options.items():
        print(f"segment_columns: {k} -> {v}")
        remaining_columns.remove(k)

    for name, dtype in df.dtypes.items():
        if name in remaining_columns:
            if dtype == np.float64:
                ... # linear interpolation
            else:
                raise Exception(f"Column {name} is of type {dtype} does not have a segmentation strategy")

    return df
