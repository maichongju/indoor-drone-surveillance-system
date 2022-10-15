from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Tuple
from pathlib import Path

from sympy import Point2D, Point3D

from cflib.drivers.crazyradio import Crazyradio

from general.enum import IntEnum, Enum, auto

import ipaddress

import re


@dataclass(frozen=True)
class Position:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @staticmethod
    def from_point2d(point: Point2D) -> Position:
        return Position(point.x, point.y)

    @staticmethod
    def from_point3d(point: Point3D) -> Position:
        return Position(point.x, point.y, point.z)

    def distance(self, other: Position) -> float:
        if not isinstance(other, Position):
            raise TypeError('other must be Position')
        diff = self - other
        distance = (diff.x ** 2 + diff.y ** 2 + diff.z ** 2) ** 0.5
        return distance

    def with_in_range(self, other: Position, range: Position, ignore_z: bool = False) -> bool:
        """ Determine if the other position is within range of this position
        Example:
        >>> Position(0, 0, 0).with_in_range(Position(1, 1, 1), Position(2, 2, 2))
        True
        >>> Position(0, 0, 0).with_in_range(Position(1, 1, 1), Position(0.5, 0.5, 0.5))
        False
        >>> Position(0, 0, 0).with_in_range(Position(1, 1, 1), Position(0.5, 0.5, 200), ignore_z=True)
        True

        """
        if not isinstance(other, Position):
            raise TypeError('other must be Position')
        if not isinstance(range, Position):
            raise TypeError('range must be Position')

        diff = (self.abs() - other.abs()).abs()
        if ignore_z:
            return diff.x <= range.x and diff.y <= range.y

        return diff <= range

    def abs(self) -> Position:
        return Position(abs(self.x), abs(self.y), abs(self.z))

    def to_point2d(self) -> Point2D:
        return Point2D(self.x, self.y)

    def to_point3d(self) -> Point3D:
        return Point3D(self.x, self.y, self.z)

    def to_json(self, indent: int = 4) -> str:
        """Return the Position object in json.
        """
        return json.dumps(self, default=lambda o: o.__dict__, indent=indent)

    def __lt__(self, other: Position) -> bool:
        if not isinstance(other, Position):
            raise TypeError('other must be Position')

        return self.x < other.x and self.y < other.y and self.z < other.z

    def __gt__(self, other: Position) -> bool:
        if not isinstance(other, Position):
            raise TypeError('other must be Position')
        return self.x > other.x and self.y > other.y and self.z > other.z

    def __le__(self, other: Position) -> bool:
        if not isinstance(other, Position):
            raise TypeError('other must be Position')
        return self.x <= other.x and self.y <= other.y and self.z <= other.z

    def __ge__(self, other: Position) -> bool:
        if not isinstance(other, Position):
            raise TypeError('other must be Position')
        return self.x >= other.x and self.y >= other.y and self.z >= other.z

    def __sub__(self, other: Position | int) -> Position:
        if not isinstance(other, Position) and not isinstance(other, int):
            raise TypeError('Invalid type')
        if isinstance(other, int):
            return Position(self.x - other, self.y - other, self.z - other)
        return Position(self.x - other.x, self.y - other.y, self.z - other.z)

    def __add__(self, other: Position | int) -> Position:
        if not isinstance(other, Position) and not isinstance(other, int):
            raise TypeError('Invalid type')
        if isinstance(other, int):
            return Position(self.x + other, self.y + other, self.z + other)
        return Position(self.x + other.x, self.y + other.y, self.z + other.z)

    def to_csv(self):
        x = f'{self.x:.3f}' if self.x is not None else 'None'
        y = f'{self.y:.3f}' if self.y is not None else 'None'
        z = f'{self.z:.3f}' if self.z is not None else 'None'
        return f'{x},{y},{z}'

    def __str__(self) -> str:
        x = f'{self.x:.3f}' if self.x is not None else 'None'
        y = f'{self.y:.3f}' if self.y is not None else 'None'
        z = f'{self.z:.3f}' if self.z is not None else 'None'

        return f"({x}, {y}, {z})"


@dataclass
class AxisDirection:
    axis: Axis | None = None
    direction: Direction | None = None

    def is_complete(self) -> bool:
        """Determines if the axis and direction are set
        """
        return self.axis is not None and self.direction is not None

    @staticmethod
    def x_positive() -> AxisDirection:
        return AxisDirection(Axis.X, Direction.POSITIVE)

    @staticmethod
    def x_negative() -> AxisDirection:
        return AxisDirection(Axis.X, Direction.NEGATIVE)

    @staticmethod
    def y_positive() -> AxisDirection:
        return AxisDirection(Axis.Y, Direction.POSITIVE)

    @staticmethod
    def y_negative() -> AxisDirection:
        return AxisDirection(Axis.Y, Direction.NEGATIVE)

    @staticmethod
    def from_yaw(yaw: float) -> AxisDirection:
        """Get the axis and direction base on the given yaw value.
        This return to the nearest axis base and split by the 45 degree mark.
        ```
                       0 (X, Positive)
                       ^
        (Y, Positive)  |
               +90 <---|---> -90 (Y, Negative)
                       |
                       v
                       180 (X, Negative)
        ```
        -45 <= yaw <= 45: X Positive
        -135 <= yaw <= -45: Y Negative
        45 <= yaw <= 135: Y Positive
        -180 <= yaw <= -135 or 135 <= yaw <= 180: X Negative
        """
        if -45 <= yaw and yaw <= 45:
            return AxisDirection(Axis.X, Direction.POSITIVE)
        elif -135 <= yaw and yaw <= -45:
            return AxisDirection(Axis.Y, Direction.NEGATIVE)
        elif 45 <= yaw and yaw <= 135:
            return AxisDirection(Axis.Y, Direction.POSITIVE)
        else:
            return AxisDirection(Axis.X, Direction.NEGATIVE)

    def rotate_right(self) -> AxisDirection:
        if not self.is_complete():
            raise ValueError('Axis and direction must be set')

        if self.axis == Axis.X:
            if self.direction == Direction.POSITIVE:  # x+
                return AxisDirection(Axis.Y, Direction.NEGATIVE)
            else:  # x-
                return AxisDirection(Axis.Y, Direction.POSITIVE)
        else:
            if self.direction == Direction.POSITIVE:  # y+
                return AxisDirection(Axis.X, Direction.POSITIVE)
            else:  # y-
                return AxisDirection(Axis.X, Direction.NEGATIVE)

    def rotate_left(self) -> AxisDirection:
        if not self.is_complete():
            raise ValueError('Axis and direction must be set')

        if self.axis == Axis.X:
            if self.direction == Direction.POSITIVE:  # x+
                return AxisDirection(Axis.Y, Direction.POSITIVE)
            else:  # x-
                return AxisDirection(Axis.Y, Direction.NEGATIVE)
        else:
            if self.direction == Direction.POSITIVE:  # y+
                return AxisDirection(Axis.X, Direction.NEGATIVE)
            else:  # y-
                return AxisDirection(Axis.X, Direction.POSITIVE)

    def reset(self):
        self.axis = None
        self.direction = None


class Axis(Enum):
    X = auto(),
    Y = auto(),
    Z = auto()


class Direction(IntEnum):
    """Direction of the axis
    """
    POSITIVE = 1
    NEGATIVE = -1


class GDirection(IntEnum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3
    SAME = 4


def position_from_dict(json: dict) -> Position:
    """Load the position from a dict (part of the json)

    Args:
        json (dict): json decoded dict

    Returns:
        Position: Position object
    """
    if not isinstance(json, dict):
        raise TypeError('json must be a dict')
    if 'x' not in json or 'y' not in json or 'z' not in json:
        raise ValueError('json must contain x, y and z')
    x = float(json['x'])
    y = float(json['y'])
    z = float(json['z'])

    return Position(x, y, z)


def is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except Exception:
        return False


def has_dongle() -> bool:
    """ Check if Crazyfile dongle is connected
    """
    try:
        Crazyradio()
    except Exception:
        return False
    return True


def is_same_sign(a: float | int, b: float | int) -> bool:
    """Check if two numbers have the same sign
    """
    return (a < 0) == (b < 0)


def percentage_cal(value: float, min_value: float, max_value: float, invert: bool = False) -> float:
    """Calculate the percentage of the value in the range of max and min value from min value. 
    If the value is larger than the max value, then the percentage will be 1. If the value is  
    smaller than the min value then the percentage will be 0. If the invert is `True`, the 
    behavior will be the other way around.

    Args:
        value (float): value to calculate
        max_value (float): maximum value
        min_value (float): minimum value
        invert (bool, optional): invert the behavior. Defaults to False.

    Examples:
        >>> percentage_cal(0.2, 0, 1)
        0.2
        >>> percentage_cal(0.3, 0, 1, True)
        0.7

    """
    if max_value == min_value:
        raise ValueError("max_value and min_value cannot be the same")

    if not invert:
        if value <= min_value:
            return 0

        elif value >= max_value:
            return 1

        return (value - min_value) / (max_value - min_value)

    else:
        if value >= max_value:
            return 0

        elif value <= min_value:
            return 1

        return (max_value - value) / (max_value - min_value)


def rotate_axis_coord(x: float, y: float, degree: float):
    """Generate the new coordinate after rotating the given degree around the origin
    """

    radian = math.radians(degree)

    x, y = -y, x

    new_x = -x * math.cos(radian) + y * math.sin(radian)
    new_y = x * math.sin(radian) + y * math.cos(radian)

    return (new_y, new_x)


def point_relevant_location_yaw(p1: Position, p2: Position, yaw: float) -> GDirection:
    """This function only consider 2d plane. It will return the relevant direction 
    of the point. this consider the yaw of the drone 
    Example:
        >>> point_location(Position(1,1), Position(2,1))
        POSITIVE
    """
    p1 = rotate_axis_coord(p1.x, p1.y, -yaw)
    p2 = rotate_axis_coord(p2.x, p2.y, -yaw)

    if p1[1] > p2[1]:  # right of p1
        return GDirection.EAST
    elif p1[1] < p2[1]:  # Left of p1
        return GDirection.WEST
    else:  # Same line
        return GDirection.SAME


def point_relevant_location(p1: Position, p2: Position, yaw: float = 0) -> Tuple[GDirection, GDirection]:
    """Return the relevant location of p2 to p1. Return are [x-axis,y-axis]
    """

    if yaw != 0:
        temp_p1 = rotate_axis_coord(p1.x, p1.y, -yaw)
        temp_p2 = rotate_axis_coord(p2.x, p2.y, -yaw)
        p1 = Position(temp_p1[0], temp_p1[1], p1.z)
        p2 = Position(temp_p2[0], temp_p2[1], p2.z)

    x_axis = GDirection.SAME
    if p2.x > p1.x:
        x_axis = GDirection.NORTH
    elif p2.x < p1.x:
        x_axis = GDirection.SOUTH

    y_axis = GDirection.SAME
    if p2.y > p1.y:
        y_axis = GDirection.WEST
    elif p2.y < p1.y:
        y_axis = GDirection.EAST

    return (x_axis, y_axis)


def ensure_folder_exist(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)


def get_yaw_from_axis_direction(axis_direction: AxisDirection) -> float:
    """Get the yaw from the axis direction
    """
    if not axis_direction.is_complete():
        raise ValueError('axis_direction is not complete')
    if axis_direction.axis == Axis.X:
        if axis_direction.direction == Direction.POSITIVE:
            return 0
        else:
            return 180
    elif axis_direction.axis == Axis.Y:
        if axis_direction.direction == Direction.NEGATIVE:
            return 90
        else:
            return -90


def round_up(n: int | float, round_num: int | float) -> float | int:
    """Round up to the nearest round_num
    Parameters:
        n (int|float): number to round up
        round_num (int|float): round to the nearest round_num

    Example:
    >>> round_up(12, 10)
    20
    >>> round_up(6, 5)
    10
    """


def create_file(path: str, content: str | None = None):
    """Create a file with the content (optional)

    Args:
        path (str): Path to the file 
        content (str | None, optional): Content to be write. Defaults to None.
    """

    with open(path, 'w') as f:
        if content is not None:
            f.write(content)


def validate_ip(ip: str) -> bool:
    """Validate the ip address

    Args:
        ip (str): ip address

    Returns:
        bool: True if the ip is valid
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def get_ip_address(string: str) -> str:
    """
    Get the ip address from the string
    """
    ip = re.findall(r'[0-9]+(?:\.[0-9]+){3}', string)
    if len(ip) == 0:
        return ''
    return ip[0]
