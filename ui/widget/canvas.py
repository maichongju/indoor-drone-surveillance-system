from __future__ import annotations

import time
from random import choice
from typing import List

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from vispy import scene
from vispy.color import ColorArray

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


class Canvas3DVispy(scene.SceneCanvas):
    TEXT_OFFSET = (0.1, 0.1, 0)

    def __init__(self, plane_size: int = 10,
                 x_range: tuple = (0, 5),
                 y_range: tuple = (0, 5),
                 z_range: tuple = (0, 1)):
        super().__init__(keys='interactive', show=True)
        self.unfreeze()
        self._colors = [
            ColorArray('#27CACE'), ColorArray('#872D85'),
            ColorArray('#DB734B'), ColorArray('#5816BB'),
            ColorArray('#BDAFED'), ColorArray('#B657C6'),
            ColorArray('#079DE2'), ColorArray('#EE4881')]

        self._view = self.central_widget.add_view()
        self._view.bgcolor = '#ffffff'
        self._view.camera = scene.TurntableCamera(
            distance=10.0,
            up='+z',
        )
        floor = scene.visuals.Plane(
            width=plane_size,
            height=plane_size,
            width_segments=plane_size,
            height_segments=plane_size,
            color=(0.5, 0.5, 0.5, 0.1),
            edge_color=(0.5, 0.5, 0.5, 0.5),
            parent=self._view.scene)

        xax = scene.Axis(pos=[[x_range[0], 0], [x_range[1], 0]], tick_direction=(0, -1), axis_color='r', tick_color='r',
                         text_color='r',
                         font_size=14, axis_label='x', parent=self._view.scene)
        yax = scene.Axis(pos=[[0, y_range[0]], [0, y_range[1]]], tick_direction=(-1, 0), axis_color='g', tick_color='g',
                         text_color='g',
                         font_size=14, axis_label='y', parent=self._view.scene)

        zax = scene.Axis(pos=[[z_range[0], 0], [-z_range[1], 0]], tick_direction=(0, -1), axis_color='b',
                         tick_color='b', text_color='b',
                         font_size=14, parent=self._view.scene)
        zax.transform = scene.transforms.MatrixTransform()
        zax.transform.rotate(90, (0, 1, 0))
        zax.transform.rotate(-45, (0, 0, 1))

        self.marker = None
        self.lines = []

        self.plot_line([[1, 1, 1], [1, 2, 1], [2, 2, 1], [2, 1, 1]])

        self.freeze()

    def plot_scatter(self, points: List):
        if not isinstance(points, list) and \
                not len(points) == 3 and \
                not isinstance(points[0], list) and \
                not isinstance(points[1], list) and \
                not isinstance(points[2], list) and \
                not len(points[0]) == len(points[1]) == len(points[2]):
            raise TypeError(f'points must be a list with format [[x1,x2...,xn],[y1,y2...yn],[z1,z2...zn]]')
        self.clear_marker()
        marker = []

        for x, y, z in zip(points[0], points[1], points[2]):
            # self.add_marker(x, y, z)
            marker.append((x, y, z))

        scene.visuals.Markers(
            pos=np.array(marker),
            size=5,
            face_color=ColorArray("#4d90fa"),
            parent=self._view.scene,
        )

    def plot_line(self, points: List, connect_head_tail: bool = False):
        """
        Draw the lines with the given points, lines are connected to each other in order
        Args:
            points: 2D list containing the points
            connect_head_tail: connect the head and tail of the points
        Returns:
        """
        if not isinstance(points, list):
            raise TypeError(f'points must be a list with format [[x1,x2...,xn],[y1,y2...yn],[z1,z2...zn]]')
        points = points.copy()
        color = self.get_random_color()
        if connect_head_tail:
            points.append(points[0])

        line = scene.visuals.Line(
            pos=np.array(points),
            color=color,
            width=3,
            parent=self._view.scene,
        )

        # No need to draw the text for the last point
        if connect_head_tail:
            points.pop()

        marker = scene.visuals.Markers(
            pos=np.array(points),
            size=10,
            face_color=color,
            parent=self._view.scene,
        )
        line = VispyLine(line, marker)

        for point in points:
            string = f'({point[0]:.2f},{point[1]:.2f},{point[2]:.2f})'
            text = scene.visuals.Text(
                text=string,
                pos=self._get_text_pos(point),
                color='black',
                font_size=10,
                parent=self._view.scene,
            )
            line.add_text(text)

        self.lines.append(line)

    def _get_text_pos(self, point: tuple):
        return point[0] + self.TEXT_OFFSET[0], point[1] + self.TEXT_OFFSET[1], point[2] + self.TEXT_OFFSET[2]

    def clear_marker(self):
        if self.marker is not None:
            self.marker.parent = None
            self.marker = None

    def get_random_color(self):
        return choice(self._colors)


class VispyLine:
    """
    Helper class to draw save information for a line in vispy.
    """

    def __init__(self, line: scene.Line, marker: scene.Markers = None, name: str = None):
        self._parent = line.parent
        self.line = line
        self.text = []
        self.marker = marker
        self.name = name

    def set_line_visible(self, visible: bool):
        self.line.parent = self._parent if visible else None

    def set_marker_visible(self, visible: bool):
        if self.marker is not None:
            self.marker.parent = self._parent if visible else None

    def set_text_visible(self, visible: bool):
        for text in self.text:
            text.parent = self._parent if visible else None

    def add_text(self, text: scene.Text):
        self.text.append(text)

    def clear(self):
        self.line.parent = None
        for t in self.text:  # type: scene.Text
            t.parent = None
        if self.marker is not None:
            self.marker.parent = None
