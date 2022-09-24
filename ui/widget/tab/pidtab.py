
import time

from general.cflib import CFParameter
from hub.drone import Drone
from PyQt6.QtWidgets import QGridLayout, QLabel, QLineEdit, QPushButton
from ui.widget.tab.tab import Tab

from copy import deepcopy


class PIDTab(Tab):

    def __init__(self, drone: Drone, parent=None):
        super().__init__(name=drone.name, parent=parent)
        self._drone = drone

        self.text_map = {}
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QGridLayout(self)
        self.setLayout(main_layout)
        row = 0

        for value in CFParameter:
            main_layout.addWidget(QLabel(value.name), row, 0)
            self.text_map[value.name] = QLineEdit()
            if self._drone.is_connect:
                self.text_map[value.name].setText(
                    self._drone.get_parameter(value))
            main_layout.addWidget(self.text_map[value.name], row, 1)
            button = QPushButton("Set")
            # _ is needed because QT always pass False for button click
            button.clicked.connect(lambda _ = value, value = value: self._btn_set_onclick(value, float(
                self.text_map[value.name].text()), self.text_map[value.name]))
            main_layout.addWidget(button, row, 2)

            row += 1

    def _btn_set_onclick(self, parameter: CFParameter, value: float, text_edit: QLineEdit):
        self._drone.set_paramter(parameter, value)
        time.sleep(0.1)
        value = self._drone.get_parameter(parameter)
        text_edit.setText(value)
