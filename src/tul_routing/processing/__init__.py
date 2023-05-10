from ..config import Config
from ..logging import logger


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

    def run(self):
        pass