# https://www.pythonguis.com/pyqt6-tutorial/


import logging
from logging import Handler

import jsonpickle
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QTextCursor
from PyQt6.QtWidgets import (QApplication, QGroupBox, QHBoxLayout, QMainWindow,
                             QMessageBox, QPlainTextEdit, QPushButton,
                             QTabWidget, QVBoxLayout, QWidget)

from config import Config
from general.utils import has_dongle, ensure_file_exist
from hub.hub import Hub
from hub.location import LOCATIONS
from map.path import PathList
from log.logger import LOGGER
from ui.widget.dialog import LocationDialog, PathDialog
from ui.widget.tab.dronetab import DroneWidget
from ui.widget.tab.monitortab import MonitorTab
from ui.widget.tunepid import TunePID
from ui.widget.window.debugwindow import DebugWindow
from ui.widget.window.flightdatawindow import FlightDataWindow
from ui.widget.window.realtimemapwindow import RealTimeMapWindow

PATH_FILE_PATH = "paths.json"
PATH_FILE_DEFAULT = []


class GUI(QApplication):
    def __init__(self, hub: Hub, config: Config, start_check=True):
        super().__init__([])
        self._error = False
        self._hub = hub
        self.window = MainWindow(hub, config)
        # self.aboutToQuit.connect(self.close_event)
        self.window.setFixedSize(self.window.sizeHint())
        self.setWindowIcon(QIcon("./ui/icons/drone.png"))
        if start_check:
            self.check_dongle()

    def check_dongle(self):
        if not has_dongle():
            self._error = True
            QMessageBox.critical(None,
                                 "Dongle Error",
                                 "No dongle found, please connect one and restart the application.")

    def close_event(self):
        self._hub.disconnectAll()

    def exec(self):
        if not self._error:
            self.window.show()
            super().exec()


class MainWindow(QMainWindow):
    """Main windows of the program"""

    def __init__(self, hub: Hub, config: Config):
        super().__init__()
        self._config = config
        self._hub = hub
        self._debug_window = DebugWindow(self._hub)
        self._real_time_window = None
        self._setup_ui()
        self._setup_menu()

        if config.get_gui_value('show_on_start'):
            self._debug_window.show()

    def _setup_ui(self):
        self.setWindowTitle('Drone Server')
        # self.setGeometry(300, 300, 300, 200)

        # Need a dummy widget to hold a layout
        dummy = QWidget()

        main_layout = QVBoxLayout()

        gb_log = QGroupBox("Message")
        self.logger_widget = QPlainTextEdit(parent=gb_log)
        logger_handler = LogHandler(self.logger_widget)
        logger_handler.signals.log_update.connect(self._add_to_log)
        logging.getLogger().addHandler(logger_handler)

        self.tab = QTabWidget()

        for drone in self._hub.drones.values():
            drone_widget = DroneWidget(drone, self)
            self.tab.addTab(drone_widget, drone_widget.name)

        if len(self._hub.drones) > 0:
            self.tab.widget(0).set_is_showing(True)
        size = self.tab.widget(0).sizeHint()
        # monitor tab
        monitorTab = MonitorTab(self._hub, size)
        self.tab.insertTab(0, monitorTab, monitorTab.name)
        self.tab.setCurrentIndex(0)
        self.tab.currentChanged.connect(self._tab_changed)

        gb_layout = QHBoxLayout()
        gb_layout.addWidget(self.logger_widget)
        gb_log.setLayout(gb_layout)

        # logger widget setup
        self.logger_widget.setReadOnly(True)
        self.logger_widget.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.logger_widget.setMinimumHeight(100)

        logger_btn_layout = QVBoxLayout()
        gb_layout.addLayout(logger_btn_layout)

        self.btn_logger_clear = QPushButton("Clear", gb_log)
        self.btn_logger_clear.clicked.connect(self.logger_widget.clear)
        logger_btn_layout.addWidget(self.btn_logger_clear)

        self.btn_logger_save = QPushButton("Save", gb_log)
        logger_btn_layout.addWidget(self.btn_logger_save)

        logger_btn_layout.addStretch()

        main_layout.addWidget(self.tab)
        main_layout.addWidget(gb_log)
        dummy.setLayout(main_layout)

        self.setCentralWidget(dummy)

    def _setup_menu(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu('&File')

        exit_action = QAction('&Exit', self)
        exit_action.triggered.connect(QApplication.quit)

        file_menu.addAction(exit_action)

        position_menu = menu_bar.addMenu('&Position')

        location_setting_action = QAction('&Location', position_menu)
        location_setting_action.triggered.connect(self._show_location_dialog)
        position_menu.addAction(location_setting_action)

        path_setting_action = QAction('&Path', position_menu)
        path_setting_action.triggered.connect(self._show_path_dialog)
        position_menu.addAction(path_setting_action)

        tool_menu = menu_bar.addMenu('&Tool')

        flight_data_plot_action = QAction('&Flight Data Plot', tool_menu)
        flight_data_plot_action.triggered.connect(self._show_flight_data_plot)
        tool_menu.addAction(flight_data_plot_action)

        real_time_map_action = QAction('&Real Time Map', tool_menu)
        real_time_map_action.triggered.connect(self._show_real_time_map)
        tool_menu.addAction(real_time_map_action)

        debug_menu = menu_bar.addMenu('&Debug')
        # drone_menu = debug_menu.addMenu('&Drone')
        # for drone in self._hub.drones.values():
        #     drone_menu.addMenu(TestDroneMenu(drone,drone_menu))

        dump_menu = debug_menu.addMenu('&Dump')

        dump_config_action = QAction('&Config', dump_menu)
        dump_config_action.triggered.connect(lambda:
                                             LOGGER.debug(self._config.to_json())
                                             )
        dump_menu.addAction(dump_config_action)

        dump_location_action = QAction('&Location', dump_menu)
        dump_location_action.triggered.connect(lambda:
                                               LOGGER.debug(LOCATIONS.to_json(indent=None))
                                               )
        dump_menu.addAction(dump_location_action)

        debug_window_action = QAction('&Debug Window', debug_menu)
        debug_window_action.triggered.connect(self._show_debug_window)
        debug_menu.addAction(debug_window_action)

        tune_PID_action = QAction('&Tune PID', debug_menu)
        tune_PID_action.triggered.connect(self._show_tune_PID_window)
        debug_menu.addAction(tune_PID_action)

    def _show_debug_window(self):
        if self._debug_window.isVisible():
            self._debug_window.activateWindow()
        else:
            self._debug_window.show()

    def _show_tune_PID_window(self):
        self._tune_PID_window = TunePID(self._hub, parent=self)
        self._tune_PID_window.exec()

    def _show_location_dialog(self):
        dialog = LocationDialog(self)
        value = dialog.exec()

    def _show_path_dialog(self):
        raw_path = jsonpickle.encode(PATH_FILE_DEFAULT, unpicklable=False)
        ensure_file_exist(PATH_FILE_PATH, raw_path)
        with open(PATH_FILE_PATH) as f:
            path = PathList.load(f)
        dialog = PathDialog(path_list=path, parent=self)
        value = dialog.exec()

    def _show_flight_data_plot(self):
        self._window = FlightDataWindow()
        self._window.show()

    def _show_real_time_map(self):
        self._real_time_window = RealTimeMapWindow(self._hub,
                                                   close_callback=self._read_time_map_cb)
        self._real_time_window.show()

    def _read_time_map_cb(self):
        self.__real_time_window = None

    def _tab_changed(self):
        for i in range(self.tab.count()):
            self.tab.widget(i).set_is_showing(False)
        self.tab.currentWidget().set_is_showing(True)

    def _add_to_log(self, msg: str):
        self.logger_widget.moveCursor(QTextCursor.MoveOperation.End)
        self.logger_widget.insertPlainText(msg)
        self.logger_widget.moveCursor(QTextCursor.MoveOperation.End)

    def closeEvent(self, event):
        self._hub.disconnectAll()
        QApplication.closeAllWindows()
        # if self._debug_window.isVisible():
        #     self._debug_window.close()


class LogSignal(QObject):
    """Signal for when there is a new log entry"""
    log_update = pyqtSignal(str)


class LogHandler(Handler):

    def __init__(self, widget: QPlainTextEdit):
        super().__init__()
        self.signals = LogSignal()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s\n', '%Y-%m-%d %H:%M:%S')
        self.setFormatter(formatter)
        self.setLevel(logging.DRONE)
        self.widget = widget

    def emit(self, record):
        msg = self.format(record)
        try:
            self.signals.log_update.emit(msg)
        except:
            pass
