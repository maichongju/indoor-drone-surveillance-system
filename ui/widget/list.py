from __future__ import annotations

import logging
from copy import deepcopy

from PyQt6.QtWidgets import QListWidget
from PyQt6.QtWidgets import QListWidgetItem

from hub.location import LOCATIONS
from hub.location import Location


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
