from __future__ import annotations

import pandas as pd
# Must import this before importing matplotlib
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QPushButton
from pandas import DataFrame

from general.utils import df_to_list
from log import LogVariable
from ui.widget.canvas import Canvas3D
from ui.widget.canvas import Canvas3DVispy
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


class ThreeDPlotVispyTab(Tab):
    def __init__(self, parent=None):
        super().__init__('3D Plot', parent=parent)
        self.file_name = None
        self.setFixedSize(800, 600)
        self._setup_ui()

    def _setup_ui(self):
        self.canvas = Canvas3DVispy()
        layout = QHBoxLayout(self)
        layout.addWidget(self.canvas.native)
        self.setLayout(layout)

    def clear(self):
        self.canvas.clear_marker()

    def plot(self, df: DataFrame, file_name):
        headers = [
            LogVariable.POSITION_X.name,
            LogVariable.POSITION_Y.name,
            LogVariable.POSITION_Z.name,
        ]
        data = df_to_list(df, headers)
        self.canvas.plot_scatter(data)
