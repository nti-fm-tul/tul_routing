from pathlib import Path
from typing import Dict, Tuple, Union

from ..config import Config
from ..logging import logger
from ..typing import DFSegmentedTypeLike, PathLike


class TulRouting(object):
    def __init__(self, config: Config = None):
        if config is None:
            logger.warn("Using default config, which may not be suitable for production.")
            config = Config()
        
        logger.debug(f"""Using config: {config}, with 
            osrm_api_server: {config.osrm_api_server}
            open_elevation_api_server: {config.open_elevation_api_server}
            overpass_api_server: {config.overpass_api_server}
            """)

        self.config = config

    def run(self, path_like: PathLike, verbose=True, options: Dict = None) -> DFSegmentedTypeLike:
        # from feature_extraction.feature_pipeline import query_features_from_apis, drop_nearby_points
        # from speed_predictor.analytic_speed_predictor import analytic_predict
        from .feature_pipeline  import query_features_from_apis
        from ..parsing import Parser
        from ..utils.town_cache import TownCache
        from ..etl.Graph import Graph, GraphChain
        from .feature_extraction import drop_nearby_points

        parser = Parser()
        options = dict() if not options else options

        options['config'] = self.config

        def build_cache(inp):
            options['cache'] = options.get('cache', TownCache.create(options))
            return inp

        if 'dump_dataframe_to_csv' not in options:
            options['dump_dataframe_to_csv'] = False

        # create a pipeline where current step takes an input from the previous
        graph = Graph([
            # 0) build the cache
            GraphChain(build_cache),

            # 1) first load the file
            parser.parse,

            # 2) next we extract geo info
            parser.get_standardised_df,

            # 3) next we drop slow moving points
            drop_nearby_points,

            # 4) then we extract feature point using osrm, overpass and open elevation
            GraphChain(query_features_from_apis, verbose=verbose, inputs=lambda x, _: (x, verbose, options)),

            # 5) segmentation
            # GraphChain(
            #     segmentation.resample_features,
            #     inputs=lambda x, _: (x, verbose, options),
            # ),

            # # 5.1) add CAN parameters
            # GraphChain(
            #     can_params=can_params,
            #     inputs=lambda df, _: (df, options.get("can_params", dict()))
            # ),

            # # 5.2) optionally run analytic speed predictor
            # GraphChain(
            #     analytical=analytic_predict,
            #     inputs=lambda df, _: (df, options)
            # ),

            # # 6) optionally we dump the segmented data to a csv file
            # GraphChain(
            #     dump_dataframe_to_csv,
            #     # optionally will generate a file "preprocess.yyyy-mm-dd-HH-MM-SS-rnd.after-seg.csv"
            #     inputs=lambda df, _: (df, 'preprocess', '.after-seg')
            # ),

        ], verbose=verbose)

        graph.process_options(options)
        result = graph.run(path_like)

        return result