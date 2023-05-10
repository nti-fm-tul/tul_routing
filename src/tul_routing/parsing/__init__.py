from typing import Dict, Optional, Type

from ..typing import PathLike
from .abstract_parser import AbstractParser
from .csv_parser import CsvParser
from .geojson_parser import GeoJsonParser
from .gpx_parser import GpxParser
from .kml_parser import KmlParser
from .parse_type import ParseType
from .route_parser import RouteParser


def get_default_parsers() -> Dict[ParseType, Type[AbstractParser]]:
    """Supported parsers"""
    return {
        ParseType.CSV: CsvParser,
        ParseType.KML: KmlParser,
        ParseType.GPX: GpxParser,
        ParseType.JSON: RouteParser,
        ParseType.GEOJSON: GeoJsonParser,
    }


def get_supported_extensions():
    return ['.gpx', '.kml', '.tcx', '.geojson', '.csv', '.json']


def is_filename_supported(filename: str):
    name = str(filename).lower()

    return any([name.endswith(ext) for ext in get_supported_extensions()])


class Parser:
    def __init__(self):
        self.parsers = get_default_parsers()

    def get_parser(self, ptype: ParseType):
        cls = self.parsers.get(ptype)
        assert cls is not None, f"Could not find a parser fot the type {ptype}"
        return cls()

    def parse(self, path_like: PathLike, ptype: Optional[ParseType] = None) -> 'AbstractParser':
        ptype = detect_ptype(path_like) if ptype is None else ptype

        type_parser = self.get_parser(ptype)
        return type_parser.parse(path_like)

    @classmethod
    def get_standardised_df(cls, parser: 'AbstractParser'):
        return parser.get_standardised_df()



def detect_ptype(path_like: Optional[PathLike] = None) -> ParseType:
    # detect type or fails
    return ParseType(str(path_like).split(".")[-1].lower())


parser = Parser()
__all__ = ["parser", "detect_ptype", "get_default_parsers", "get_supported_extensions", "is_filename_supported"]
