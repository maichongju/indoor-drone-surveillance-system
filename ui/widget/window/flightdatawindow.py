from __future__ import annotations
import os
from pathlib import Path
import jsonpickle
from matplotlib.pyplot import set_loglevel
import general.utils as utils

from log.logger import LOGGER

set_loglevel('warning')

from ui.widget.tab.threedplottab import ThreeDPlotVispyTab
from ui.widget.tab.twodplottab import TwoDPlotTab

# Must import this before importing matplotlib
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QFileDialog, QTabWidget, QMessageBox

import traceback
import pandas as pd
from general.debug import DroneExtraLog

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

        btn_load_last = QPushButton("Load Last")
        btn_load_last.clicked.connect(self._load_last_flight_data_on_click)
        tool_layout.addWidget(btn_load_last)

        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self._clear_btn_on_click)
        tool_layout.addWidget(btn_clear)

        tool_layout.addStretch()

        tab = QTabWidget(self)
        main_layout.addWidget(tab)

        self.tab_3d = ThreeDPlotVispyTab(self)
        tab.addTab(self.tab_3d, self.tab_3d.name)

        self.tab_2d = TwoDPlotTab(self)
        tab.addTab(self.tab_2d, self.tab_2d.name)

    def _load_last_flight_data_on_click(self):
        try:
            self.clear()
            file = utils.get_sorted_file_list('logs/flight_data')[-1]
            df = self._prepare_log_files('\\'.join(file.parts))
            self._plot(df, file.name)

        except IOError:
            QMessageBox.critical(self, "Error", "Error when loading last flight data")
            LOGGER.debug(traceback.format_exc())
            return

    def _load_btn_on_click(self):
        try:
            self.clear()
            # Add file dialog (use QFileDialog)
            file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv)")
            file_name = file_path.split('/')[-1]
            if file_path == '':
                return
                # file_path = 'logs/flightdataexample.csv'
            df = self._prepare_log_files(file_name)
            self._plot(df)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error when loading file ({e})")
            LOGGER.debug(traceback.format_exc())
            self.tab_2d.clear()
            self.tab_3d.clear()

    def _plot(self, df: pd.DataFrame, file_name):
        try:
            self.lbl_file_name.setText(file_name)
            self.tab_3d.plot(df, file_name)
            self.tab_2d.plot(df, file_name)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error when plotting data ({e})")
            LOGGER.debug(traceback.format_exc())
            self.tab_2d.clear()
            self.tab_3d.clear()

    def process_extra_log(self, value: str):
        """
        Process the extra log data, convert it into a dictionary
        """
        try:
            return jsonpickle.decode(value)
        except Exception as e:
            LOGGER.debug('Invalid extra log data: %s', value)
            return {}

    def _prepare_log_files(self, log_file: str):
        df = pd.read_csv(log_file)

        df['hover.x'] = df['hover.x'].replace({'None': None}).astype(float)
        df['hover.y'] = df['hover.y'].replace({'None': None}).astype(float)
        df['hover.z'] = df['hover.z'].replace({'None': None}).astype(float)

        if 'extra' in df:  # backward compatibility
            df['extra'] = df['extra'].apply(self.process_extra_log)
        else:  # newer version
            df[DroneExtraLog.MAINTAIN_DIRECTION_OFFSET] = \
                df[DroneExtraLog.MAINTAIN_DIRECTION_OFFSET].replace({'None': None}).astype(float)
        return df

    def clear(self):
        self.lbl_file_name.setText('')
        self.tab_3d.clear()
        self.tab_2d.clear()

    def _clear_btn_on_click(self):
        self.clear()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = FlightDataWindow()
    window.show()
    sys.exit(app.exec())
