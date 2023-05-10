# TUL Routing

## Installation

```bash
pip install tul-routing
```

## Usage

```python
from tul_routing import TulRouting, Config, Parser

config = Config(
    osrm_api_server="...",
    open_elevation_api_server="...",
    overpass_api_server="..."
)

parser = Parser()
result = parser.parse("foo.kml")
print(result.get_points())
print(result.get_standardised_df())
```

### Debugging

```python
# to enable debug logging
from tul_routing import logger
logger.setLevelForAll("DEBUG")

# to disable warnings
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='tul_routing')
```