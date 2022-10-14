from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass

import jsonpickle
from general.utils import Position, position_from_dict, create_file
from log.logger import LOGGER


@dataclass
class Location:
    """Location class. If `name` is the same as another location. Then they are consider equal
    """
    name: str
    position: Position

    def __init__(self, name: str, position: Position):
        self.name = name
        self.position = deepcopy(position)

    def load(self, other: Location):
        self.name = other.name
        self.position = deepcopy(other.position)

    def to_json(self, indent: int = 4) -> str:
        return json.dumps(self, default=lambda o: o.__dict__, indent=indent)

    def __eq__(self, other: Location) -> bool:
        if not isinstance(other, Location):
            return False
        return self.name == other.name

    def __str__(self):
        return f"{self.name} at {self.position}"


def location_from_dict(json: dict) -> Location:
    """Load the object from a dict (part of the json)

    Args:
        json (dict): json decoded dict

    Returns:
        Location: the new location
    """
    if not isinstance(json, dict):
        raise TypeError('json must be a dict')
    if 'name' not in json or 'position' not in json:
        raise ValueError('json must contain name and position')

    return Location(json['name'], position_from_dict(json['position']))


class Locations:

    _default_content: str = '[]'

    def __init__(self, locations_file: str = 'locations.json'):
        self._locations = []
        self.load(locations_file)

    def load(self, locations_file: str = 'locations.json'):
        try:
            with open(locations_file, 'r') as f:
                temp_locations = json.load(f)
                self._load_from_dict(temp_locations)
        except FileNotFoundError:
            LOGGER.info(
                f'location file ({locations_file}) not found. Creating new one.')
            try:
                create_file(locations_file, self._default_content)
            except Exception as e:
                LOGGER.debug(
                    f'Create location file ({locations_file}) failed. {e}')
        except Exception:
            LOGGER.info(f"Couldn't load locations from {locations_file}.")
        finally:
            LOGGER.debug(f'{len(self._locations)} locations loaded.')

    def _load_from_dict(self, json: list):
        if not isinstance(json, list):
            raise TypeError('json must be a list')
        for location in json:
            try:
                self.add_location(location_from_dict(location))
            except Exception as e:
                LOGGER.debug(f'load location failed.')

    def save(self, locations_file: str = 'locations.json', new_location: list | Locations = None):
        """Save the location to the file. If a new location in provided, it will use that 
        location

        Args:
            locations_file (str, optional): location file. Defaults to 'locations.json'.
            new_location (list, optional): list of new Location. Defaults to None.
        """
        if new_location is not None:
            if isinstance(new_location, Locations):
                new_location = new_location.locations
            if self._is_location_valid(new_location):
                self.locations = deepcopy(new_location)
            else:
                LOGGER.info("Invalid Locations, Location is not save")
                return
        try:
            with open(locations_file, 'w') as f:
                f.write(self.to_json())
            LOGGER.debug(
                f'{len(self._locations)} locations saved to {locations_file}.')
        except Exception as e:
            LOGGER.info(f'Save locations to file failed. {e}')

    def add_location(self, location: Location):
        """Add a new location to the list. If the location already exists, nothing will happen.

        Args:
            name (str): name of the location
            position (Position): position of the location
            location (Location, optional): Use `Location` object instead. Defaults to None.

        """
        found = self.find(location.name)
        if found is not None:
            return

        self._locations.append(deepcopy(location))

    def remove_location(self, name: str):
        """Remove the location by name.

        Args:
            name (str): name of the location to be remove
        """
        index = self.find_index(name)
        if index != -1:
            self._locations.pop(index)

    def update_location(self, name: str, new_name: str = None, position: Position = None):
        """update the location, if not found then do nothing.

        Args:
            name (str): name to search
            position (Position): new location
        """

        found = self.find(name)
        if found is not None:
            print('called')
            found.name = new_name if new_name is not None else found.name
            found.position = deepcopy(
                position) if position is not None else found.position

    def existed(self, name: str) -> bool:
        """Check if the location exists
        """
        for l in self._locations:
            if l.name == name:
                return True
        return False

    def find_index(self, name: str) -> int:
        """Find the `Location` object by index. If not found, return -1.

        Args:
            name (str): location to search

        Returns:
            int: index of the location, -1 if not found
        """
        result = -1
        for i in range(len(self._locations)):
            if self._locations[i].name == name:
                result = i
        return result

    def find(self, name: str) -> Location | None:
        """Find the `Location` object by name. If not found, return `None`.

        Args:
            name (str): name to search

        Returns:
            Location | None: target location
        """
        index = self.find_index(name)
        return self._locations[index] if index != -1 else None

    def _is_location_valid(self, locations: list) -> bool:
        """Validate if the given list is a valid locations

        Args:
            locations (list): list to be check
        """
        msg = "Invalid locations. locations must be a list of location"
        if not isinstance(locations, list):
            return False
        for item in locations:
            if not isinstance(item, Location):
                return False
        return True

    def to_json(self, indent: int | None = None) -> str:
        """to json for jsonpickle 

        Args:
            indent (int | None, optional): _description_. Defaults to None.

        Returns:
            str: json string 
        """
        print('called')
        return jsonpickle.encode(self._locations, unpicklable=False, indent=indent)

    def __iter__(self):
        return iter(self._locations)

    @property
    def locations(self) -> list:
        return deepcopy(self._locations)

    @locations.setter
    def locations(self, locations: list):
        self._locations = deepcopy(locations)


# Global locations
LOCATIONS = Locations()
LOCATIONS.load()
