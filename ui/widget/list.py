from __future__ import annotations

import logging
from copy import deepcopy

from PyQt6.QtWidgets import QListWidget
from PyQt6.QtWidgets import QListWidgetItem

from general.utils import Position
from hub.location import LOCATIONS
from hub.location import Location
from hub.path import PathList, Path
from log.logger import LOGGER


class LocationListWidget(QListWidget):
    """Location List base on Location class

    """

    def __init__(self, parent=None, locations=None):
        super().__init__(parent)
        self.locations = deepcopy(LOCATIONS) if locations is None else deepcopy(locations)
        for l in self.locations.locations:
            item = LocationItem(l)
            super().addItem(item)

    def addItem(self, location: Location):
        if location is None:
            logging.debug("Adding None to LocationListWidget. Ignoring")
            return
        item = LocationItem(location)
        super().addItem(item)
        self.locations.add_location(item.location)

    def remove(self, index: int):
        """Remove the item at the given index."""
        item = super().takeItem(index)
        if item is not None:
            self.locations.remove_location(item.location.name)

    def is_empty(self) -> bool:
        """Check if the list is empty. 

        Returns:
            bool: `True` if empty, `False` otherwise
        """
        return self.count() == 0


class LocationItem(QListWidgetItem):
    def __init__(self, location: Location, parent=None):
        super().__init__(parent)
        self.location = location
        self.setText(location.text)

    def update(self):
        self.setText(self.location.text)


class PathListWidget(QListWidget):
    def __init__(self, paths: PathList, parent=None):
        super().__init__(parent=parent)
        self.paths = paths
        self.is_updated = False
        for path in self.paths.raw_paths:
            item = PathItem(path)
            super().addItem(item)

    def addItem(self, path: Path):
        item = PathItem(path)
        super().addItem(item)
        self.paths.add_path(path)

    def update_path(self, path: Path):
        """Update the path in the list. If not found, do nothing."""
        index = self.paths.find_index(path)
        if index == -1:
            LOGGER.debug(f"Path ({path.name}) not found. Ignoring")
        self.paths.raw_paths[index] = path
        self.item(index).update()
        self.item(index).path = path

    def remove(self, index: int):
        """Remove the item at the given index."""
        item = super().takeItem(index)
        if item is not None:
            self.paths.raw_paths.pop(index)

    def is_empty(self) -> bool:
        """Check if the list is empty.

        Returns:
            bool: `True` if empty, `False` otherwise
        """
        return self.count() == 0


class PathItem(QListWidgetItem):
    def __init__(self, path: Path, parent=None):
        super().__init__(parent=parent)
        self.path = path
        self.setText(path.name)

    def update(self):
        self.setText(self.path.name)


class PathDetailsListWidget(QListWidget):
    def __init__(self, path: Path = None, parent=None):
        super().__init__(parent=parent)
        self.path = None
        self.is_updated = False
        if path is not None:
            self.load(path)

    def load(self, path: Path):
        """
        Load the path into the list.
        """
        self.clear()
        self.path = path
        for pos in self.path.positions:
            location = Location(pos)
            item = LocationItem(location)
            super().addItem(item)

    def clear(self) -> None:
        """Reset the list."""
        super().clear()
        self.path = None
        self.is_updated = False


    def addItem(self, position: Position):
        location = Location(position)
        item = LocationItem(location)
        super().addItem(item)
        self.path.add_position(position)

    def remove(self, index: int):
        """Remove the item at the given index."""
        item = super().takeItem(index)
        if item is not None:
            self.path.positions.pop(index)

    def update_positions(self):
        """
        This will replace all the positions in the path with the positions in the list
        """
        if self.path is None:
            LOGGER.debug("Path is None. Ignoring")
            return

        pos = []
        for i in range(self.count()):
            item = self.item(i)
            pos.append(item.location.position)
        self.path.replace_pos_all(pos)
        self.is_updated = False
