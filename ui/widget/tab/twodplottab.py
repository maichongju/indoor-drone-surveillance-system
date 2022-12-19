import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QWidget, QScrollArea, QHBoxLayout

from general.debug import DroneExtraLog
from ui.widget.canvas import CanvasWidget, FigureType
from ui.widget.tab.tab import Tab


class TwoDPlotTab(Tab):
    def __init__(self, parent=None):
        super().__init__('2D Plot', parent=parent)

        self._canvas = []

        widget = QWidget()  # Dummy widget to hold the layout
        main_layout = QGridLayout(self)
        widget.setLayout(main_layout)

        dummy_layout = QHBoxLayout()
        scroll = QScrollArea()
        scroll.setWidget(widget)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)

        dummy_layout.addWidget(scroll)
        self.setLayout(dummy_layout)

        self.height_canvas = CanvasWidget(x_label='', y_label='different', figure_type=FigureType.PLOT,
                                          title='Height Stable')
        main_layout.addWidget(self.height_canvas, 0, 0)

        self.xy_top_canvas = CanvasWidget(x_label='y', y_label='x', figure_type=FigureType.SCATTER, title='Top View',
                                          invert_x=True)
        main_layout.addWidget(self.xy_top_canvas, 0, 1)
        self.xy_stable_canvas = CanvasWidget(x_label='', y_label='difference', figure_type=FigureType.PLOT,
                                             title='XY Stable')
        main_layout.addWidget(self.xy_stable_canvas, 1, 0)

        self.moving_direction_drift_canvas = CanvasWidget(x_label='', y_label='difference', figure_type=FigureType.PLOT,
                                                          title='Moving Direction Drift')
        main_layout.addWidget(self.moving_direction_drift_canvas, 1, 1)

        self._canvas.append(self.height_canvas)
        self._canvas.append(self.xy_top_canvas)
        self._canvas.append(self.xy_stable_canvas)
        self._canvas.append(self.moving_direction_drift_canvas)

    def plot(self, df: pd.DataFrame, file_name: str):
        size = len(df.index)

        # Height plot
        height_data = df['stateEstimate.z'].to_list()
        hover_data = df['hover.z'].to_list()
        diff_z = []
        for hover_height, z in zip(height_data, hover_data):
            diff_z.append(0 if pd.isna(hover_height) else hover_height - z)
        draw_data = {'height': {'y': diff_z}}

        self.height_canvas.plot(draw_data, file_name=file_name)

        # Top View Plot
        top_view_data = [df['stateEstimate.y'].to_list(), df['stateEstimate.x'].to_list()]
        self.xy_top_canvas.plot(top_view_data, file_name=file_name)

        # XY Stable Plot
        xy_stable_data = {}
        hover_x = df['hover.x'].to_list()
        hover_y = df['hover.y'].to_list()
        pos_x = df['stateEstimate.x'].to_list()
        pos_y = df['stateEstimate.y'].to_list()
        diff_x = []
        diff_y = []
        for hx, px, hy, py in zip(hover_x, pos_x, hover_y, pos_y):
            diff_x.append(0 if pd.isna(hx) else hx - px)
            diff_y.append(0 if pd.isna(hy) else hy - py)
        xy_stable_data['x'] = {'y': diff_x}
        xy_stable_data['y'] = {'y': diff_y}

        self.xy_stable_canvas.plot(xy_stable_data, file_name=file_name)

        # Moving Direction Drift Plot
        drift_data = []
        for log in df['extra'].to_list():  # type: dict
            drift_data.append(log.get(DroneExtraLog.MAINTAIN_DIRECTION_OFFSET, 0))

        self.moving_direction_drift_canvas.plot(drift_data, file_name=file_name)

    def clear(self):
        [canvas.clear() for canvas in self._canvas]
