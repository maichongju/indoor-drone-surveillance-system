from __future__ import annotations

import json
from typing import TextIO, Tuple

import jsonpickle

from general.utils import Position
from log.logger import LOGGER


class Path:
    """Path class to contain a list of points for the drone to fly to
    """

    def __init__(self, name: str = '', positions: list[Position] = None, connected: bool = False):
        self.name = name
        self._current = 0
        self._positions = []
        self.connected = connected

        if positions is not None:
            for position in positions:
                self.add_position(position)

    def add_position(self, point: Position):
        if not isinstance(point, Position):
            raise TypeError('point must be Position')
        self._positions.append(point.copy())

    def insert_position(self, index:int, position: Position):
        """
        Insert a position in the given position
        Args:
            index: Index that needs to be inserted
            position: position object needs to be inserted
        """
        self._positions.insert(index, position)

    def get_next_position(self) -> Position | None:
        """ Get the next point in the path. If there is no next point, `None` is returned. 
        """
        if self._current >= len(self._positions):
            return None
        point = self._positions[self._current]
        self._current += 1
        return point

    def replace_pos_all(self, pos: list[Position]):
        """
        Replace all the positions in the path with the given list of positions
        Args:
            pos: list of positions to replace
        """
        self._positions = []
        for p in pos:
            self.add_position(p.copy())

    def is_empty(self) -> bool:
        return len(self._positions) == 0

    def reset(self):
        self._current = 0

    def __getstate__(self):
        return {
            'name': self.name,
            'pos': self._positions,
            'connected': self.connected
        }

    def is_identical(self, other):
        if not isinstance(other, Path):
            return False

        if self.name != other.name:
            return False

        if len(self._positions) != len(other._positions):
            return False

        for pos1, pos2 in zip(self._positions, other._positions):
            if pos1 != pos2:
                return False

        return True

    def pos_to_list(self) -> list[Tuple[float, float, float]]:
        """Convert the position list to a list of tuples

        Returns:
            list[Tuple[float, float, float]]: list of tuples
        """
        return [p.to_tuple() for p in self._positions]

    @property
    def positions(self):
        return self._positions

    def __eq__(self, other):
        if not isinstance(other, Path):
            return False

        if self.name != other.name:
            return False

        return True


class PathList:
    def __init__(self):
        self._paths = []

    def add_path(self, path: Path | dict):
        """
        If it is Path object, then it will add it to the list. if it is a dict, then it will
        try to add it. Raise TypeError if it is not a Path or dict
        Args:
            path:

        Raises:
            TypeError: if it is not a Path or dict
            KeyError: if the dict does not contain the correct keys

        """
        if isinstance(path, Path):
            self._paths.append(path)
            return
        if isinstance(path, dict):
            if 'name' not in path or 'pos' not in path:
                raise KeyError('path must contain name and points')

            if not isinstance(path['name'], str):
                raise TypeError('name must be a string')
            if not isinstance(path['pos'], list):
                raise TypeError('pos must be a list')

            name = path['name']
            raw_pos = path['pos']
            connected = path.get('connected', False)
            positions = []
            for pos in raw_pos:  # type: dict
                positions.append(Position(pos['x'], pos['y'], pos['z']))

            self._paths.append(Path(name, positions, connected))

    @staticmethod
    def load(file: TextIO) -> PathList:
        """
        Load a path from a file. Needs to be a json file
        Args:
            file: file open in read mode
        """
        path_list = PathList()
        try:
            paths = json.load(file)
            if not isinstance(paths, list):
                raise TypeError('json must be a list')

            for path in paths:  # type: dict
                try:
                    path_list.add_path(path)
                except KeyError as e:
                    LOGGER.error(f'Fail to load path {path.get("name", "")} {e}')
                except TypeError as e:
                    LOGGER.error(f'Fail to load path. Invalid entry. {e}')

        except json.JSONDecodeError as e:
            LOGGER.error(f'Failed to load path file: {e}. Invalid json.')

        except TypeError as e:
            LOGGER.error(f'Failed to load path file: {e}. Invalid json. Needs to be a list')

        return path_list

    def find_index(self, path: Path) -> int:
        for i, p in enumerate(self._paths):
            if p == path:
                return i

        return -1

    def remove_path_by_index(self, index: int):
        self._paths.pop(index)

    def name_exists(self, name: str) -> bool:
        for path in self._paths:
            if path.name == name:
                return True
        return False

    def save(self, file: TextIO):
        """
        Save the path to a file. Needs to be a json file
        Args:
            file: file open in write mode
        """
        file.write(jsonpickle.encode(self, unpicklable=False))

    def __iter__(self):
        return iter(self._paths)

    def __getitem__(self, item):
        return self._paths[item]

    def __getstate__(self):
        return self._paths

    @property
    def size(self):
        return len(self._paths)

    def is_empty(self):
        return len(self._paths) == 0

    @property
    def raw_paths(self):
        return self._paths
