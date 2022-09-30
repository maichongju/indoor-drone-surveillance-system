from __future__ import annotations
from typing import List
from log.logger import LOGGER

# Must import this before importing matplotlib
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QFileDialog

import pandas as pd
# from hub import Hub
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# from general.utils import ensure_folder_exist
import time 

from ui.widget.tab.tab import Tab

EXPORT_FOLDER = 'export'


class ThreeDPlotTab(Tab):
    def __init__(self, parent = None):
        super().__init__('3D Plot', parent = parent)
        self.file_name = None
        self._setup_ui()

        
    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)
        
        canvas_layout = QVBoxLayout()
        main_layout.addLayout(canvas_layout)
        
        self.canvas = Canvas()
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
        
    def plot(self, positions: List, file_name:str):
        self.canvas.plot(positions)
        self.file_name = file_name
        
        
class Canvas(FigureCanvas):
    def __init__(self,):
        self.fig = Figure(figsize=(6, 6))
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_xlabel('Y')
        self.ax.set_ylabel('X')
        self.ax.set_zlabel('Z')
        
    def plot(self, points):
        self.ax.clear()
        size = len(points[0])
        for i in range(size):
            self.ax.scatter(points[0][i], -points[1][i], points[2][i])

        
        self.draw()
            
    def to_top_down(self):
        self.ax.view_init(-90, -90)
        self.draw()
        
    def to_side_view_Y(self):
        self.ax.view_init(0, -90)
        self.draw()
        
    def to_side_view_X(self):
        self.ax.view_init(0, 0)
        self.draw()
        
    def clear(self):
        self.ax.clear()
        self.draw()
        
    def save(self, source_file_name ):
        if source_file_name is None:
            return
        # ensure_folder_exist(EXPORT_FOLDER)
        cur_time = time.strftime('%Y%m%d%H%M%S')
        self.fig.savefig(f'{EXPORT_FOLDER}/{source_file_name}_3d_{cur_time}.png')
        LOGGER.debug(f'3D plot saved to {EXPORT_FOLDER}/{source_file_name}_3d_{cur_time}.png')