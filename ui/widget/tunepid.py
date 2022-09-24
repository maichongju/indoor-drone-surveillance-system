from __future__ import annotations

from ui.widget.tab.pidtab import PIDTab
from hub.hub import Hub

from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QTabWidget
from PyQt6.QtWidgets import QVBoxLayout


class TunePID(QDialog):
    def __init__(self, hub: Hub, parent = None):
        super().__init__(parent= parent)
        
        self._hub = hub
        self._setup_ui()        
        self.setWindowTitle("Tune PID")
        self.setFixedSize(self.sizeHint())
        
    def _setup_ui(self):
        self._tab = QTabWidget(self)
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        main_layout.addWidget(self._tab)
        
        for drone in self._hub.drones.values():
            tab = PIDTab(drone, self)
            self._tab.addTab(tab, tab.name)
            if not drone.is_connect:
                tab.setEnabled(False)
            
        