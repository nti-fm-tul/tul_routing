# TUL Routing

## About

The TUL Routing library represents an advanced tool for route data processing, developed with a focus on flexibility and extensibility in processing and analyzing routing information. The primary goal of the library is to provide users with an easy yet powerful way to manipulate routing data, enrich it with contextual information, and customize the output for a broad range of applications, from simple mapping to complex analytical tasks.

This library is designed to be user-friendly for those who may not be deeply familiar with routing system programming yet robust enough to handle sophisticated route manipulation. It facilitates detailed configuration for connecting to external services like OSRM for route mapping, Open Elevation for elevation data, and Overpass API for additional metadata from OpenStreetMap.

A pivotal library feature is the route enrichment system that allows users to define custom functions for adding contextual information to routes based on way and node tags. This provides significant flexibility and enables the tailoring of the resulting dataset to the specific needs of the application.

Route segmentation, a key library functionality, allows the division of data into consistent and analyzable segments. The system offers various segmentation methods, enabling users to choose the approach that best matches the nature of their data and analysis requirements.

## Installation

```bash
pip install tul-routing
```

## Usage

```python
from tul_routing import TulRouting, Config, SegmentationKind, EnrichOptions
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
    
    segmentation_options=dict(
        max_segment_length=SegmentationKind.LINEAR,
        max_segment_duration=SegmentationKind.ONCE,
    ),
)

# 2) run the routing 
tul_routing = TulRouting(config)
result = tul_routing.run(path_to_the_file, options=dict(), verbose=1)

# 3) print the data frame
print(result)
```
