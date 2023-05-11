import json
from pandas.core.frame import DataFrame
import requests
from ..config import Config


class OpenElevationUtils(object):
    def __init__(self, config: Config):
        self.config = config

    def label_elevation(self, df: DataFrame) -> DataFrame:
        """Gets all pairs 'latitude', 'longitude' from input DataFrame and makes a POST
        request to Open-Elevation API at open_elevation_api_server address. Parses elevation
        data from response and adds them to the input DataFrame.
        uses #https://earthexplorer.usgs.gov/ SRTM 1 arc second data

        Args:
            df (DataFrame): Trace DataFrame, must contain columns 'latitude', 'longitude'

        Returns:
            DataFrame: Input trace DataFrame with new column containing elevation of coordinates
        """
        api_server = f'{self.config.open_elevation_api_server}/api/v1/lookup'

        # POST limits number of points sent in request to 2100, using batches
        coordinates = df[['latitude', 'longitude']].to_dict(orient='records')
        elevations = []

        for i in range(0, df.shape[0], 2000):
            payload = {'locations': coordinates[i:i + 2000]}
            res = requests.post(api_server, json=payload, timeout=self.config.request_timeout)
            res_json = json.loads(res.text)
            batch_elevations = [r['elevation'] for r in res_json['results']]
            elevations += batch_elevations

        df['elevation'] = elevations

        return df