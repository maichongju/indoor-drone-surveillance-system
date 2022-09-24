
from PyQt6.QtWidgets import QWidget

class Tab(QWidget):
    def __init__(self,name,parent=None):
        super().__init__(parent)
        self._showing = False
        self.name = name
    
    def set_is_showing(self, is_showing: bool):
        self._showing = is_showing
        
    def is_showing(self) -> bool:
        return self._showing