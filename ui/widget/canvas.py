from __future__ import annotations

import time
from typing import List

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from general.enum import Enum, auto
from general.utils import ensure_folder_exist
from log.logger import LOGGER

EXPORT_FOLDER = 'export'


class FigureType(Enum):
    SCATTER = auto()
    PLOT = auto()


class CanvasWidget(QWidget):
    def __init__(self, x_label: str,
                 y_label: str,
                 figure_type: FigureType,
                 title: str = None,
                 invert_x: bool = False,
                 invert_y: bool = False,
                 parent=None):
        super().__init__(parent=parent)
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        # main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_layout = QHBoxLayout()
        main_layout.addLayout(lbl_layout)
        lbl_layout.addStretch()
        lbl_title = QLabel(title)
        lbl_layout.addWidget(lbl_title)
        lbl_layout.addStretch()

        if figure_type == FigureType.SCATTER:
            self.canvas = Canvas2DScatter(x_label, y_label, invert_x, invert_y, title)
        else:
            self.canvas = Canvas2DPlot(x_label, y_label, title)
        main_layout.addWidget(self.canvas)

        btn_layout = QHBoxLayout()
        main_layout.addLayout(btn_layout)
        btn_layout.addStretch()

        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.btn_save_clicked)
        btn_layout.addWidget(btn_save)

        btn_layout.addStretch()

        self._file_name = None

    def plot(self, points: List | dict, file_name: str):
        self._file_name = file_name
        self.canvas.plot(points)

    def btn_save_clicked(self):
        if self._file_name is None or self._file_name == '':
            return
        self.canvas.save(self._file_name)

    def clear(self):
        self.canvas.clear()


class Canvas2D(FigureCanvas):
    def __init__(self,
                 x_label: str,
                 y_label: str,
                 title: str = None):
        self.fig = Figure(figsize=(6, 3))
        super().__init__(self.fig)

        self.ax = self.fig.add_subplot(111)

        self.ax.set_xlabel(x_label)
        self.ax.set_ylabel(y_label)
        self.x_label = x_label
        self.y_label = y_label
        self.title = title
        self.fig.tight_layout()
        self.ax.grid(axis='both')

    def plot(self, points: dict | List):
        self.ax.cla()
        self.ax.set_xlabel(self.x_label)
        self.ax.set_ylabel(self.y_label)
        self.ax.set_title(self.title)
        self.ax.grid(axis='both')

    def save(self, source_file_name: str):
        if source_file_name is None:
            return
        ensure_folder_exist(EXPORT_FOLDER)
        if not self.title:
            self.title = f'{self.x_label}{self.y_label}'

        file_name = f'{EXPORT_FOLDER}/{source_file_name}_{self.title}_{time.time()}.png'
        self.fig.savefig(file_name)
        LOGGER.info(f'Saved to {file_name}')

    def clear(self):
        self.ax.cla()
        self.draw()

    def draw(self):
        self.fig.tight_layout()
        super().draw()


class Canvas2DPlot(Canvas2D):
    def __init__(self,
                 x_label: str,
                 y_label: str,
                 title: str = None):
        super().__init__(x_label, y_label, title)

    def plot(self, points: dict, legend: str = None):
        """
        Plot the 2d points with the given data points. Pass dist when need more than one
        set of data with the label as the key. then use show legend to decide whether to
        show the legend or not.

        Args:
            points: the points to plot
            legend: the legend location. see https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.legend.html for
            more info
        """
        super().plot(points)
        if not isinstance(points, dict):
            raise ValueError(f'points must be a list, not {type(points)}')

        for label, value in points.items():  # type: str, dict
            if not isinstance(value, dict):
                raise ValueError(f'points must be a dict, not {type(value)}')

            if 'x' not in value:
                self.ax.plot(value['y'], label=label)
            elif 'x' in value and 'y' in value:
                self.ax.plot(value['x'], value['y'], label=label)

        if legend is not None:
            self.ax.legend(loc=legend)
        self.draw()


class Canvas2DScatter(Canvas2D):
    def __init__(self,
                 x_label: str,
                 y_label: str,
                 invert_x: bool = False,
                 invert_y: bool = False,
                 title: str = None):
        super().__init__(x_label, y_label, title)

        if invert_x:
            self.ax.invert_xaxis()
        if invert_y:
            self.ax.invert_yaxis()

    def plot(self, points: List):
        super().plot(points)
        size = len(points[0])
        for i in range(size):
            self.ax.scatter(points[0][i], points[1][i], c='#5895fc', s=2)
        self.draw()


class Canvas3D(FigureCanvas):
    def __init__(self, ):
        self.fig = Figure(figsize=(8, 8))
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.invert_xaxis()
        self.ax.set_xlabel('Y')
        self.ax.set_ylabel('X')
        self.ax.set_zlabel('Z')

    def plot(self, points):
        self.ax.clear()
        size = len(points[0])
        for i in range(size):
            self.ax.scatter(points[0][i], points[1][i], points[2][i])

        self.ax.set_xlabel('Y')
        self.ax.set_ylabel('X')
        self.ax.set_zlabel('Z')
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

    def save(self, source_file_name):
        if source_file_name is None:
            return
        ensure_folder_exist(EXPORT_FOLDER)
        cur_time = time.strftime('%Y%m%d%H%M%S')
        self.fig.savefig(
            f'{EXPORT_FOLDER}/{source_file_name}_3d_{cur_time}.png')
        LOGGER.debug(
            f'3D plot saved to {EXPORT_FOLDER}/{source_file_name}_3d_{cur_time}.png')
