from __future__ import annotations

from matplotlib.pyplot import set_loglevel

set_loglevel('warning')

from ui.widget.tab.threedplottab import ThreeDPlotTab
from ui.widget.tab.twodplottab import TwoDPlotTab

# Must import this before importing matplotlib
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QFileDialog, QTabWidget

import pandas as pd

EXPORT_FOLDER = 'export'


class FlightDataWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Flight Data")
        # self._hub = hub
        self._setup_ui()
        self.setFixedSize(self.sizeHint())

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        tool_layout = QHBoxLayout()
        main_layout.addLayout(tool_layout)

        btn_load = QPushButton("Load")
        btn_load.clicked.connect(self._load_btn_on_click)
        tool_layout.addWidget(btn_load)

        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self._clear_btn_on_click)
        tool_layout.addWidget(btn_clear)

        tool_layout.addStretch()

        tab = QTabWidget(self)
        main_layout.addWidget(tab)

        self.tab_3d = ThreeDPlotTab(self)
        tab.addTab(self.tab_3d, self.tab_3d.name)

        self.tab_2d = TwoDPlotTab(self)
        tab.addTab(self.tab_2d, self.tab_2d.name)

    def _load_btn_on_click(self):
        # Add file dialog (use QFileDialog)
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv)")
        file_name = file_path.split('/')[-1]
        if file_path == '':
            return
            # file_path = 'logs/flightdataexample.csv'
        df = pd.read_csv(file_path)

        df['hover.x'] = df['hover.x'].replace({'None': None}).astype(float)
        df['hover.y'] = df['hover.y'].replace({'None': None}).astype(float)
        df['hover.z'] = df['hover.z'].replace({'None': None}).astype(float)
        self.tab_3d.plot(df, file_name)
        self.tab_2d.plot(df, file_name)

    def _clear_btn_on_click(self):
        self.tab_3d.clear()
        self.tab_2d.clear()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = FlightDataWindow()
    window.show()
    sys.exit(app.exec())
