from __future__ import annotations

from PyQt6.QtWidgets import QTabWidget
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

from hub.hub import Hub
from .tab.debugtab import DebugTab


class DebugWindow(QWidget):
    def __init__(self, hub: Hub, parent = None):
        super().__init__(parent= parent)
        self.setWindowTitle("Debug Window")
        self._hub = hub
        self._setup_ui()
        
    def _setup_ui(self):
        self._tab = QTabWidget(self)
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        main_layout.addWidget(self._tab)
        
        for drone in self._hub.drones.values():
            tab = DebugTab(drone, self)
            self._tab.addTab(tab, tab.name)
            