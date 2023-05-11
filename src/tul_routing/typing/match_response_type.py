from enum import Enum
from typing import List, Optional
try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict


class GeometryType(Enum):
    LINE_STRING = "LineString"


class Geometry(TypedDict):
    coordinates: List[List[float]]
    type: GeometryType


class DatasourceName(Enum):
    LUA_PROFILE = "lua profile"


class Metadata(TypedDict):
    datasource_names: List[DatasourceName]


class Annotation(TypedDict):
    metadata: Metadata
    nodes: List[int]
    datasources: List[int]
    speed: List[float]
    weight: List[float]
    duration: List[float]
    distance: List[float]


class DrivingSide(Enum):
    LEFT = "left"
    RIGHT = "right"
    SLIGHT_LEFT = "slight left"
    SLIGHT_RIGHT = "slight right"
    STRAIGHT = "straight"


class Lane(TypedDict):
    valid: bool
    indications: List[DrivingSide]


class Intersection(TypedDict):
    entry: List[bool]
    bearings: List[int]
    location: List[float]
    out: Optional[int]
    intersection_in: Optional[int]
    lanes: Optional[List[Lane]]


class ManeuverType(Enum):
    ARRIVE = "arrive"
    DEPART = "depart"
    NEW_NAME = "new name"
    TURN = "turn"


class Maneuver(TypedDict):
    bearing_after: int
    location: List[float]
    bearing_before: int
    type: ManeuverType
    modifier: Optional[DrivingSide]


class Mode(Enum):
    DRIVING = "driving"


class Step(TypedDict):
    intersections: List[Intersection]
    driving_side: DrivingSide
    geometry: Geometry
    mode: Mode
    duration: float
    maneuver: Maneuver
    weight: float
    distance: float
    name: int


class Leg(TypedDict):
    annotation: Annotation
    steps: List[Step]
    distance: float
    duration: float
    summary: str
    weight: float


class Matching(TypedDict):
    confidence: float
    geometry: Geometry
    legs: List[Leg]
    distance: float
    duration: float
    weight_name: str
    weight: float


class Tracepoint(TypedDict):
    alternatives_count: int
    waypoint_index: int
    matchings_index: int
    location: List[float]
    name: int
    distance: float
    hint: str


class OSRMMatchResponse(TypedDict):
    """
    OSRM response type generated mostly via https://app.quicktype.io/
    """
    code: str
    message: Optional[str]
    matchings: List[Matching]
    tracepoints: List[Tracepoint]
