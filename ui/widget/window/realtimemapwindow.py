from PyQt6 import QtGui
from PyQt6.QtWidgets import QWidget, QHBoxLayout

from hub.hub import Hub
from ui.widget.canvas import Canvas3DVispy


class RealTimeMapWindow(QWidget):
    def __init__(self, hub: Hub, parent=None, close_callback=None):
        super().__init__(parent=parent)
        self._setup_ui()
        self._close_callback = close_callback
        self._hub = hub
        self.setMinimumSize(480, 360)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._close_callback is not None:
            self._close_callback()
        event.accept()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)

        self._canvas = Canvas3DVispy()
        main_layout.addWidget(self._canvas.native)
