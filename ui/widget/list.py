from __future__ import annotations

import logging
from copy import deepcopy

from PyQt6.QtWidgets import QListWidget
from PyQt6.QtWidgets import QListWidgetItem

from general.utils import Position
from hub.location import LOCATIONS
from hub.location import Location
from map.path import PathList, Path
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

    def get_selected_path(self):
        """Get the selected path. `None` if no path is selected.

        Returns:
            Path: The selected path. `None` if no path is selected.
        """
        if self.currentItem() is None:
            return None
        return self.currentItem().path

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
        self.path: Path | None = None
        self.temp_path: Path | None = path.copy() if path is not None else None
        self.is_updated = False
        if path is not None:
            self.load(path)

    def load(self, path: Path):
        """
        Load the path into the list.
        """
        self.clear()
        self.path = path
        self.temp_path = path.copy()
        for pos in self.temp_path.positions:
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
        self.temp_path.add_position(position)

    def move_current_up(self):
        """Move the current item up."""
        current_row = self.currentRow()

        # if nothing selected or already at the top
        if current_row == -1 or current_row == 0:
            return

    def swap_item(self, row1: int, row2: int):
        """Swap the two items at the given rows."""

        item1 = self.item(row1)
        item2 = self.item(row2)
        temp_item = item1.location
        item1.location = item2.location
        item2.location = temp_item
        item1.update()
        item2.update()
        self.temp_path.swap(row1, row2)

    def insertItem(self, row: int, position: Position) -> None:
        location = Location(position)
        item = LocationItem(location)
        super().insertItem(row, item)
        self.temp_path.insert_position(row, position)

    def takeItem(self, row: int) -> QListWidgetItem:
        item = super().takeItem(row)
        self.temp_path.positions.pop(row)
        return item

    def remove(self, index: int):
        """Remove the item at the given index."""
        item = super().takeItem(index)
        if item is not None:
            self.temp_path.positions.pop(index)

    def apply_change(self):
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

    def update_pos_at_index(self, index: int, pos: Position):
        self.temp_path.positions[index] = pos
        self.item(index).location.position = pos
        self.item(index).update()
        self.is_updated = True
