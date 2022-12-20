from __future__ import annotations

import pandas as pd
# Must import this before importing matplotlib
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QPushButton
from pandas import DataFrame

from general.utils import df_to_list
from hub.drone import GoToAction, FlyMode
from log import LogVariable
from general.debug import DroneExtraLog
from ui.widget.canvas import Canvas3D
from ui.widget.canvas import Canvas3DVispy, VispyMarker
from ui.widget.color import VispyColor, Color
from ui.widget.tab.tab import Tab

# from hub import Hub

EXPORT_FOLDER = 'export'


class ThreeDPlotTab(Tab):
    def __init__(self, parent=None):
        super().__init__('3D Plot', parent=parent)
        self.file_name = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)

        canvas_layout = QVBoxLayout()
        main_layout.addLayout(canvas_layout)

        self.canvas = Canvas3D()
        canvas_layout.addWidget(self.canvas)

        toolbar_layout = QVBoxLayout()
        main_layout.addLayout(toolbar_layout)

        btn_save = QPushButton("Save")
        btn_save.clicked.connect(lambda: self.canvas.save(self.file_name))
        toolbar_layout.addWidget(btn_save)

        toolbar_layout.addStretch()

        btn_top_down = QPushButton("Top Down")
        btn_top_down.clicked.connect(lambda: self.canvas.to_top_down())
        toolbar_layout.addWidget(btn_top_down)

        btn_side_view = QPushButton("Side View (Y)")
        btn_side_view.clicked.connect(lambda: self.canvas.to_side_view_Y())
        toolbar_layout.addWidget(btn_side_view)

        btn_side_view = QPushButton("Side View (X)")
        btn_side_view.clicked.connect(lambda: self.canvas.to_side_view_X())
        toolbar_layout.addWidget(btn_side_view)

    def clear(self):
        self.canvas.clear()
        self.file_name = None

    def plot(self, df: pd.DataFrame, file_name: str):
        cols = ['stateEstimate.x', 'stateEstimate.y', 'stateEstimate.z']
        values = []
        for col in cols:
            values.append(df[col].values.tolist())
        self.canvas.plot(values)
        self.file_name = file_name


COLOR_GO_TO_MOVING = VispyColor.get_color(Color.ANDROID_GREEN)
COLOR_GO_TO_HOLD = VispyColor.get_color(Color.BEE_YELLOW)
COLOR_GO_TO_AXIS_CHANGING = VispyColor.get_color(Color.BRILLIANT_ROSE)


class ThreeDPlotVispyTab(Tab):
    def __init__(self, parent=None):
        super().__init__('3D Plot', parent=parent)
        self.file_name = None
        self.setFixedSize(800, 600)
        self._setup_ui()
        self._markers = {
            FlyMode.TARGET.name: {}
        }

    def _setup_ui(self):
        self.canvas = Canvas3DVispy()
        layout = QHBoxLayout(self)
        layout.addWidget(self.canvas.native)
        self.setLayout(layout)

    def clear(self):
        for marker in self._markers.values():  # type: str, VispyMarker
            if isinstance(marker, VispyMarker):
                marker.clear()
            elif isinstance(marker, dict):
                for marker2 in marker.values():
                    marker2.clear()

    def plot(self, df: DataFrame, file_name):
        temp_dict = {
            FlyMode.TARGET.name: {
                GoToAction.HOLD.name: [[], [], []],
                GoToAction.MOVING.name: [[], [], []],
                GoToAction.AXIS_CHANGING.name: [[], [], []],
            }
        }

        backward_capable = True if 'extra' in df else False
        if backward_capable:
            headers = [
                LogVariable.POSITION_X.name,
                LogVariable.POSITION_Y.name,
                LogVariable.POSITION_Z.name,
                'mode',
                'extra',
            ]
        else:
            headers = [
                LogVariable.POSITION_X.name,
                LogVariable.POSITION_Y.name,
                LogVariable.POSITION_Z.name,
                'mode',
                DroneExtraLog.GO_TO_MODE.value,
            ]

        data = df_to_list(df, headers)

        for x, y, z, mode, extra in zip(*data):
            if mode not in temp_dict:
                temp_dict[mode] = [[], [], []]

            if mode == FlyMode.TARGET.name:
                go_to_mode = extra.get(DroneExtraLog.GO_TO_MODE.value, None) if backward_capable else extra
                match go_to_mode:
                    case GoToAction.HOLD.name:
                        self.add_xyz_to_list(x, y, z, temp_dict[mode][GoToAction.HOLD.name])
                    case GoToAction.MOVING.name:
                        self.add_xyz_to_list(x, y, z, temp_dict[mode][GoToAction.MOVING.name])
                    case GoToAction.AXIS_CHANGING.name:
                        self.add_xyz_to_list(x, y, z, temp_dict[mode][GoToAction.AXIS_CHANGING.name])
            else:
                self.add_xyz_to_list(x, y, z, temp_dict[mode])

        for mode, data in temp_dict.items():
            if mode == FlyMode.TARGET.name:
                for action, coord in data.items():
                    if len(coord[0]) > 0:
                        match action:
                            case GoToAction.HOLD.name:
                                self._markers[mode][action] = self.canvas.plot_scatter(coord,
                                                                                       {'face_color': COLOR_GO_TO_HOLD})
                            case GoToAction.MOVING.name:
                                self._markers[mode][action] = self.canvas.plot_scatter(coord,
                                                                                       {'face_color': COLOR_GO_TO_MOVING})
                            case GoToAction.AXIS_CHANGING.name:
                                self._markers[mode][action] = self.canvas.plot_scatter(coord, {
                                    'face_color': COLOR_GO_TO_AXIS_CHANGING})
            else:
                self._markers[mode] = self.canvas.plot_scatter(data)

    def add_xyz_to_list(self, x: float, y: float, z: float, target: list):
        target[0].append(x)
        target[1].append(y)
        target[2].append(z)

    def set_go_visible(self, visible: bool):
        # self.canvas.set_go_visible(visible)
        pass
