import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable


def _env_or_default(name: str, default: str | Path) -> str:
    return os.environ[name] if name in os.environ else str(default)


# define api server urls
_server_url = "http://viroco.nti.tul.cz"

osrm_api_server = _env_or_default('OSRM_API_URL', f'{_server_url}:5555')

open_elevation_api_server = _env_or_default('OPEN_ELEVATION_API_URL', f'{_server_url}:8080')

overpass_api_server = _env_or_default('OVERPASS_API_URL', f"{_server_url}:12345")

request_timeout = float(_env_or_default("REQUEST_TIMEOUT", "30"))
""" default request timeout in seconds, need to be passed to the methods manually """

osrm_location_limit = 20_000

# define data files
datadir = Path(_env_or_default('TUL_ROUTING_DATA_DIR', Path(os.getcwd(), 'data')))
datafiles_file = lambda filename: str(datadir / filename)


@dataclass
class ParseOptions:
    ...


class SegmentationKind(Enum):
    LINEAR = 'linear'
    NEAREST = 'nearest'
    ONCE = 'once'


SegmentationsOptions = dict[str, SegmentationKind]


@dataclass
class EnrichOptions:
    way_enrichment: Callable[[dict], dict] = lambda x: dict()
    node_enrichment: Callable[[dict], dict] = lambda x: dict()


@dataclass
class Config:
    osrm_api_server: str = osrm_api_server
    open_elevation_api_server: str = open_elevation_api_server
    overpass_api_server: str = overpass_api_server
    request_timeout: float = request_timeout
    osrm_location_limit: int = osrm_location_limit
    drop_unwanted_columns: bool = True

    segmentation_options: SegmentationsOptions = field(default_factory=lambda: dict())
    parse_options: ParseOptions = field(default_factory=lambda: ParseOptions())
    enrich_options: EnrichOptions = field(default_factory=lambda: EnrichOptions())
