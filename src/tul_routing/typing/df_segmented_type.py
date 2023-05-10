from pandas import Series

class DFSegmentedType:
    @classmethod
    def columns(cls):
        return [
            cls.latitude,
            cls.longitude,
            cls.speed_osrm,
            cls.speed_osrm_filtered,
            cls.way_maxspeed,
            cls.elevation,
            cls.fwd_azimuth,
            cls.way_type,
            cls.way_surface,
            cls.node_railway,
            cls.node_crossing,
            cls.node_highway,
            cls.node_intersection,
            cls.start_stop,
            cls.azimuth_diff,
            cls.elevation_diff,
            cls.speed_target
        ]

    latitude: Series = "latitude"
    longitude: Series = "longitude"
    speed_osrm: Series = "speed_osrm"
    speed_osrm_filtered: Series = "speed_osrm_filtered"
    way_maxspeed: Series = "way_maxspeed"
    elevation: Series = "elevation"
    fwd_azimuth: Series = "fwd_azimuth"
    way_type: Series = "way_type"
    way_surface: Series = "way_surface"
    node_railway: Series = "node:railway"
    node_crossing: Series = "node:crossing"
    node_highway: Series = "node:highway"
    node_intersection: Series = "node:intersection"
    start_stop: Series = "start_stop"
    azimuth_diff: Series = "azimuth_diff"
    elevation_diff: Series = "elevation_diff"
    speed_target: Series = "speed_target"