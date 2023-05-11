import math
import haversine
from ..typing import DFLatLongTypeLike, PointType


def get_distance(p1: PointType, p2: PointType):
    return haversine.haversine(p1, p2, unit='m')


def get_path_length(nodes: DFLatLongTypeLike, lat_col="latitude", lon_col="longitude"):
    nodes = nodes[[lat_col, lon_col]]
    a = nodes.drop(axis=0, index=0)
    b = nodes.drop(axis=0, index=len(nodes) - 1)
    distance = 0.0
    for a0, b0 in zip(a.values, b.values):
        distance += get_distance(a0, b0)
    return distance


def map_path_to_distance(nodes: DFLatLongTypeLike, lat_col="latitude", lon_col="longitude"):
    nodes = nodes[[lat_col, lon_col]]
    a = nodes.drop(axis=0, index=0)
    b = nodes.drop(axis=0, index=len(nodes) - 1)
    return list(get_distance(a, b) for a, b in zip(a.values, b.values))


def get_intermediate_point(p1: PointType, p2: PointType, f):
    """Returns point between p1 and p2 with distance of f/dist(p1, p2) from p1"""
    degrees_to_radians = math.pi / 180.0
    # phi = 90 - latitude
    phi1 = p1[0] * degrees_to_radians
    phi2 = p2[0] * degrees_to_radians
    # theta = longitude
    theta1 = p1[1] * degrees_to_radians
    theta2 = p2[1] * degrees_to_radians

    delta = get_distance(p1, p2) / 63710088

    a = math.sin((1-f) * delta) / math.sin(delta)
    b = math.sin(f * delta) / math.sin(delta)
    x = a * math.cos(phi1) * math.cos(theta1) + b * math.cos(phi2) * math.cos(theta2)
    y = a * math.cos(phi1) * math.sin(theta1) + b * math.cos(phi2) * math.sin(theta2)
    z = a * math.sin(phi1) + b * math.sin(phi2)
    return (math.atan2(z, math.sqrt(x**2 + y**2)) / degrees_to_radians,
            math.atan2(y, x) / degrees_to_radians)


def get_road_curvature(position1, position2, position3=None):
    """ Returns angle at position2 defined by the next two other positions.
        Based on finding an angles of triangle."""
    if position3 is None:
        # if there isn't a third point, it's considered as straight line and the angle is 0°
        return 0

    azimuth1 = get_azimuth(position1, position2)
    azimuth2 = get_azimuth(position1, position3)
    angle = azimuth2 - azimuth1
    if angle > 180:
        return angle - 360
    elif angle <= -180:
        return angle + 360
    else:
        return angle


def get_azimuth(node1: PointType, node2: PointType):
    lat1, lon1 = node1
    lat2, lon2 = node2

    d_lon = lon2 - lon1
    azim = math.atan2(math.sin(d_lon) * math.cos(lat2),
                      math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon))
    return azim / math.pi * 180


class DataInOnePoint:
    def __init__(self, position):
        self.rows = []
        self.position = position

    def set_parameter(self, param_name, value):
        for row in self.rows:
            row[param_name] = value


def get_point(row) -> PointType:
    return row.latitude, row.longitude


def group_by_position(data: DFLatLongTypeLike):
    data_iter = iter([row for _, row in data.iterrows()])
    first_row = next(data_iter)
    grouped_data = [DataInOnePoint(get_point(first_row))]
    grouped_data[-1].rows.append(first_row)

    for row in data_iter:
        pos = get_point(row)
        if pos != grouped_data[-1].position:
            grouped_data.append(DataInOnePoint(pos))
        grouped_data[-1].rows.append(row)

    return grouped_data


