
from hub.hub import Hub
from .tab import Tab

from ..widget import DroneStreamWidget

from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtCore import QSize

STREAM_WIDGET_STYLE = """
QFrame#VideoStreamWidget{
    border: 1px solid #e1e1ea;
    border-radius: 5px;
}

"""

class MonitorTab(Tab):
    def __init__(self,
                 hub: Hub,
                 tab_size: QSize,
                 row: int = 2,
                 col: int = 3):
        super().__init__("Monitor")
        self.setFixedSize(tab_size)
        self._size = (tab_size.width(), tab_size.height())
        self._col = col
        self._row = row
        self._hub = hub
        self._setup_ui()

    
    def _setup_ui(self):
        layout = QGridLayout(self)
        self.setLayout(layout)
        
        row = 1
        col = 1
        count = 0
        total = self._row * self._col
        # (Width, Height)
        size = (int(self._size[0]/self._col)-30, int(self._size[1]/self._row)-30)
        drones = list(self._hub.drones.values())
        self._drone_widgets = []
        for drone in drones[:6]:
            stream = DroneStreamWidget(drone, 
                                       stream_resolution = size, 
                                       display_name=True, 
                                       style_sheet=STREAM_WIDGET_STYLE,
                                       always_show_original_stream=True)
            self._drone_widgets.append(stream)
            layout.addWidget(stream, row, col)
            col += 1
            count += 1
            if (col > self._col):
                row += 1
                col = 1
        
        # Fill the gap
        for _ in range(count, total):
            stream = DroneStreamWidget(None, stream_resolution = size, style_sheet=STREAM_WIDGET_STYLE)
            layout.addWidget(stream, row, col)
            col += 1
            count += 1
            if (col > self._col):
                row += 1
                col = 1
    
    def set_is_showing(self, is_showing: bool):
        self._showing = is_showing
        [widget.set_visible(is_showing) for widget in self._drone_widgets]
        
                    
        
    
    