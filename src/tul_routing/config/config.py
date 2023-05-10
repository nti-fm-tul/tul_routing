import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path


def _env_or_default(name: str, default: str):
    return os.environ[name] if name in os.environ else default

# define api server urls
_server_url = "http://viroco.nti.tul.cz"

osrm_api_server = _env_or_default('OSRM_API_URL', f'{_server_url}:5555')

open_elevation_api_server = _env_or_default('OPEN_ELEVATION_API_URL', f'{_server_url}:8080')

overpass_api_server = _env_or_default('OVERPASS_API_URL', f"{_server_url}:12345")


@dataclass
class Config:
    osrm_api_server: str = osrm_api_server
    open_elevation_api_server: str = open_elevation_api_server
    overpass_api_server: str = overpass_api_server