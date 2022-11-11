from __future__ import annotations

import time
from random import choice
from typing import List, Tuple

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from vispy import scene
from vispy.color import ColorArray

from general.enum import Enum, auto
from general.utils import ensure_folder_exist, Position
from hub.path import Path
from log.logger import LOGGER
from .color import Color, VispyColor

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


DEFAULT_LINE_SETTING = {
    'width': 3,
}

DEFAULT_END_POINT_SETTING = {
    'size': 5,
}

DEFAULT_MARKER_SETTING = {
    'size': 5,
}

DEFAULT_TEXT_SETTING = {
    'color': 'black',
    'font_size': 10
}

DEFAULT_HIGH_LIGHT_SETTING = {
    'face_color': VispyColor.get_color(Color.ORANGE),
    'size': 10
}


class Canvas3DVispy(scene.SceneCanvas):
    TEXT_OFFSET = (0.1, 0.1, 0)

    def __init__(self, plane_size: int = 10,
                 x_range: tuple = (0, 5),
                 y_range: tuple = (0, 5),
                 z_range: tuple = (0, 1),
                 size: tuple = (800, 600)):
        super().__init__(keys='interactive', show=True, size=size)
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

        # self.plot_line([[1, 1, 1]])

        self.freeze()

    def plot_scatter(self, points: List):
        if not isinstance(points, list) and \
                not len(points) == 3 and \
                not isinstance(points[0], list) and \
                not isinstance(points[1], list) and \
                not isinstance(points[2], list) and \
                not len(points[0]) == len(points[1]) == len(points[2]):
            raise TypeError(f'points must be a list with format [[x1,y1,z1],[x2,y2,z2],...[xn,yn,zn]]')
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

    def plot_point(self, pos: Tuple[float, float, float]) -> scene.Markers:
        """
        Plot a single marker at the given position
        """
        return scene.visuals.Markers(
            pos=np.array([pos]),
            size=10,
            face_color=ColorArray("#ED7014"),
            parent=self._view.scene,
        )

    def plot_line(self, points: List,
                  connect_head_tail: bool = False,
                  show_endpoint: bool = True,
                  show_endpoint_text: bool = True,
                  line_settings: dict = None,
                  text_settings: dict = None,
                  endpoint_settings: dict = None,
                  use_random_color: bool = True,
                  vline: VispyLine = None) -> VispyLine | None:
        """
        Draw the lines with the given points, lines are connected to each other in order. If line is given,
        then it will update the line instead creating a new one.
        Args:
            use_random_color: whether to use random color for the line if no color is given
            vline: Vispy line to use for drawing
            points: 2D list containing the points
            connect_head_tail: connect the head and tail of the points
            show_endpoint_text: Show the endpoint text
            show_endpoint: Show the endpoint
        Returns:
        """
        if not isinstance(points, list):
            raise TypeError(f'points must be a list with format [[x1,y1,z1],[x2,y2,z2],...[xn,yn,zn]]')
        if len(points) > 0 and not isinstance(points[0], (list, tuple)):
            raise TypeError(f'points must be a list with format [[x1,y1,z1],[x2,y2,z2],...[xn,yn,zn]]')

        # Process all the setting. If no setting is given, use the default setting
        if line_settings is None:
            line_settings = DEFAULT_LINE_SETTING.copy()
        if text_settings is None:
            text_settings = DEFAULT_TEXT_SETTING.copy()
        if endpoint_settings is None:
            endpoint_settings = DEFAULT_END_POINT_SETTING.copy()

        if use_random_color and vline is None:
            color = VispyColor.get_random_color()
            if 'color' not in line_settings:
                line_settings['color'] = color
            if 'color' not in text_settings:
                text_settings['color'] = color
            if 'face_color' not in endpoint_settings:
                endpoint_settings['face_color'] = color

        if len(points) == 0:
            points = None

        if vline is None:
            # no points yet, create a placeholder
            if points is None:
                line = scene.Line(
                    pos=None,
                    parent=self._view.scene,
                    **line_settings
                )
                endpoint = scene.Markers(
                    pos=None,
                    parent=self._view.scene if show_endpoint else None,
                    **endpoint_settings
                )
                return VispyLine(
                    line=line,
                    endpoint=endpoint,
                    line_settings=line_settings,
                    endpoint_settings=endpoint_settings,
                    text_settings=text_settings,
                )
            else:  # No vline create new vline
                if connect_head_tail:
                    points.append(points[0])
                line = scene.Line(
                    pos=np.array(points),
                    parent=self._view.scene,
                    **line_settings
                )
                if connect_head_tail:
                    points.pop()
                endpoint = scene.Markers(
                    pos=np.array(points),
                    parent=self._view.scene if show_endpoint else None,
                    **endpoint_settings
                )
                vline = VispyLine(
                    line=line,
                    endpoint=endpoint,
                    line_settings=line_settings,
                    endpoint_settings=endpoint_settings,
                    text_settings=text_settings,
                )
        else:  # vline is not None, update the original line
            if points is None:  # No points, equal to clear the line
                vline.clear()
                return vline
            else:
                if connect_head_tail:
                    points.append(points[0])
                vline.line.set_data(pos=np.array(points), **line_settings)
                if connect_head_tail:
                    points.pop()
                vline.endpoint.set_data(pos=np.array(points), **endpoint_settings)
                vline.endpoint.parent = self._view.scene if show_endpoint else None

        # update text
        vline.clear_text()
        for p in points:
            string = f'({p[0]:.2f},{p[1]:.2f},{p[2]:.2f})'
            text = scene.visuals.Text(
                string,
                pos=self._get_text_pos(p),
                parent=self._view.scene if show_endpoint_text else None,
                **text_settings
            )
            vline.add_text(text)

        return vline

    def _get_text_pos(self, point: tuple):
        return point[0] + self.TEXT_OFFSET[0], point[1] + self.TEXT_OFFSET[1], point[2] + self.TEXT_OFFSET[2]

    def plot_path(self, path: Path, vispy_path: VispyPath) -> VispyPath:
        """
        Plot the path
        Args:
            path:
            vispy_path:

        Returns:
            VispyLine object representing the path
        """
        points = path.pos_to_list()
        if vispy_path is None:
            line = self.plot_line(points, connect_head_tail=path.connected)
            return VispyPath(line, path, parent=self._view.scene)
        else:
            vispy_path.line = self.plot_line(points, connect_head_tail=path.connected, vline=vispy_path.line)
            return vispy_path

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

    def __init__(self, line: scene.Line,
                 endpoint: scene.Markers,
                 name: str = None,
                 line_settings: dict = None,
                 text_settings: dict = None,
                 endpoint_settings: dict = None):
        self.parent = line.parent
        self.line = line
        self.text = []
        self.endpoint = endpoint
        self.name = name
        self.color = line.color
        self.line_settings = line_settings
        self.text_settings = text_settings
        self.endpoint_settings = endpoint_settings

    def set_line_visible(self, visible: bool):
        if self.line is not None:
            self.line.parent = self.parent if visible else None

    def set_endpoint_visible(self, visible: bool):
        if self.endpoint is not None:
            self.endpoint.parent = self.parent if visible else None

    def set_text_visible(self, visible: bool):
        for text in self.text:
            text.parent = self.parent if visible else None

    def clear_text(self):
        for text in self.text:
            text.parent = None
        self.text = []

    def add_text(self, text: scene.Text):
        self.text.append(text)

    def clear(self):
        self.line.set_data(pos=None)
        self.endpoint.set_data(pos=None)
        self.clear_text()


class VispyPath:
    def __init__(self, line: VispyLine, path: Path, parent):
        self._parent = parent
        self.line = line
        self._path = path
        self.highlight_setting = DEFAULT_HIGH_LIGHT_SETTING.copy()
        self.highlight_pos = scene.Markers(
            pos=None,
            parent=self._parent,
            **self.highlight_setting,
        )

    def set_highlight_pos(self, pos: Position):
        self.highlight_pos.set_data(
            pos=np.array([pos.to_tuple()]),
            **self.highlight_setting
        )
        self.highlight_pos.parent = self._parent

    def clear_highlight_pos(self):
        self.highlight_pos.set_data(pos=None)
        self.highlight_pos.parent = None

    def clear(self):
        if self.line is not None:
            self.line.clear()
        if self.highlight_pos is not None:
            self.highlight_pos.parent = None
            self.highlight_pos = None

    def update(self, path: Path):
        pass
