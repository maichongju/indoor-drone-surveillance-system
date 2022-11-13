import time
from dataclasses import dataclass
from threading import Thread

from PyQt6 import QtGui
from PyQt6.QtWidgets import QWidget, QHBoxLayout

from hub.hub import Hub, Drone
from log.logger import LOGGER
from ui.widget.canvas import Canvas3DVispy, VispyMarker


class RealTimeMapWindow(QWidget):
    def __init__(self, hub: Hub, parent=None, close_callback=None):
        super().__init__(parent=parent)
        self._setup_ui()
        self._close_callback = close_callback
        self._hub = hub
        self._ui_thread = _RealTimeMapUpdatingThread(self._canvas, self._hub)
        self.setMinimumSize(480, 360)
        self._ui_thread.start()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._close_callback is not None:
            self._close_callback()
        LOGGER.debug("Stopping real time map updating thread")
        self._ui_thread.stop()
        self._ui_thread.join()
        LOGGER.debug("Real time map updating thread stopped")
        event.accept()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)

        self._canvas = Canvas3DVispy()
        main_layout.addWidget(self._canvas.native)


class _RealTimeMapUpdatingThread(Thread):
    def __init__(self, canvas: Canvas3DVispy, hub: Hub):
        super().__init__()
        self._canvas = canvas
        self._hub = hub
        self._terminate = False

        self._drone_markers = []
        for drone in self._hub.drones.values():  # type: Drone
            self._drone_markers.append(_DroneMarker(drone, None))

    def run(self):
        # marker =None
        while not self._terminate:
            for drone_marker in self._drone_markers:
                drone = drone_marker.drone
                marker = drone_marker.marker
                if drone.is_connect:
                    drone_marker.marker = self._canvas.plot_point(drone.state.position.to_tuple(), setting={'size': 15},
                                                                  vmarker=marker)

            time.sleep(0.1)

            # Debug Purpose
            # pos = [random.randint(0,3) for _ in range(3)]
            # marker = self._canvas.plot_point(pos,setting={'size':15}, vmarker=marker)
            # time.sleep(1)

    def stop(self):
        self._terminate = True


@dataclass
class _DroneMarker:
    drone: Drone
    marker: VispyMarker
