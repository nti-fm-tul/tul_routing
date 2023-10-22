import pandas as pd
from ..config import Config


def segment_columns(df: pd.DataFrame, options: Config) -> pd.DataFrame:
    print("resample_features...")

    for k, v in options.segmentation_options.items():
        print(f"resample_features: {k} -> {v}")

    return df
