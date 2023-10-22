# TUL Routing

## Installation

```bash
pip install tul-routing
```

## Usage

```python
from tul_routing import TulRouting, Config, logger, EnrichOptions
logger.set_level_for_all("DEBUG")

# 0) define the path to the file
path_to_the_file = "file_name.kml"


def way_enrichment(way_tags) -> dict:
    return {
        'way_source': way_tags.get('source', "<unknown>"),
        'maxspeed': float(way_tags.get('maxspeed', -1)),
        'surface': way_tags.get('surface', "<unknown>"),
     }

def node_enrichment(node_tags) -> dict:
    return {
        'node_source': node_tags.get('source', "<unknown>"),
     }


# 1) define the config
config = Config(
    osrm_api_server="<your_osrm_server>",
    open_elevation_api_server="<your_open_elevation_server>",
    overpass_api_server="<your_overpass_server>",

    enrich_options=EnrichOptions(
        way_enrichment=way_enrichment,
        node_enrichment=node_enrichment,
    ),
)

# 2) run the routing 
tul_routing = TulRouting(config)
result = tul_routing.run(path_to_the_file, options=dict(), verbose=1)

# 3) print the data frame
print(result)
```