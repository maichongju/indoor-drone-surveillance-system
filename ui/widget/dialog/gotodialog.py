from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QLineEdit, QWidget, QTabWidget, \
    QMessageBox

import setting
from general.enum import Enum
from general.utils import Axis, Position
from hub.drone import Drone
from hub.location import Location, LOCATIONS
from hub.path import PathList, Path
from log.logger import LOGGER
from ui.icon import Icon
from ui.widget.dialog.locationeditdialog import LocationEditDialog
from ui.widget.list import LocationListWidget, LocationItem
from ui.widget.widget import PathEditWidget


class _Icon(Enum):
    CURRENT_LOCATION = Icon.DOWNLOAD


class GoToDialog(QDialog):
    """Dialog for go to a location.
    """

    class Mode(Enum):
        POSITION = 0
        PATH = 1

    def __init__(self, drone: Drone, parent=None):
        super().__init__(parent)
        self._drone = drone
        self.setWindowTitle("Go to location")
        self.position = None
        self._setup_ui()
        self.resize(self._get_tab_size(add_height=50))
        self.mode = self.Mode.POSITION
        self.result: Path | Location | None = None

    def _setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # self._path_widget = self._get_path_tab()

        # tabs.addTab(self._get_position_tab(), "Position")
        self.tabs.addTab(self._get_position_tab(), "Position")
        # self.tabs.addTab(self._path_widget, "Path")

        self.tabs.currentChanged.connect(lambda index: self.tab_change_cb(index))

        self.bottom_layout = QHBoxLayout()
        layout.addLayout(self.bottom_layout)

        self.bottom_layout.addStretch()

        self.btn_start = QPushButton("Start")
        self.btn_start.clicked.connect(self.accept)
        self.bottom_layout.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.bottom_layout.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.save)
        self.bottom_layout.addWidget(self.btn_save)

    def _get_position_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)

        center_layout = QHBoxLayout()
        layout.addLayout(center_layout)

        cord_layout = QVBoxLayout()
        center_layout.addLayout(cord_layout)

        cord_layout.addWidget(QLabel("Enter the destination location"))
        # location_layout = QHBoxLayout()
        # cord_layout.addLayout(location_layout)

        self.pos_x = PositionLabelEditSetWidget("X:", parent=self)
        self.pos_x.btn.clicked.connect(lambda: self._position_btn_click_callback(Axis.X))
        self.pos_x.btn.setToolTip("Get current X position")
        cord_layout.addWidget(self.pos_x)

        self.pos_y = PositionLabelEditSetWidget("Y:", parent=self)
        self.pos_y.btn.clicked.connect(lambda: self._position_btn_click_callback(Axis.Y))
        self.pos_y.btn.setToolTip("Get current Y position")
        cord_layout.addWidget(self.pos_y)

        self.pos_z = PositionLabelEditSetWidget("Z:", parent=self)
        self.pos_z.btn.clicked.connect(lambda: self._position_btn_click_callback(Axis.Z))
        self.pos_z.btn.setToolTip("Get current Z position")
        cord_layout.addWidget(self.pos_z)

        self.btn_add_to_list = QPushButton("Add")
        self.btn_add_to_list.clicked.connect(self._add_btn_click_callback)
        cord_layout.addWidget(self.btn_add_to_list)

        cord_layout.addStretch()

        # Layout for location list
        right_layout = QHBoxLayout()
        center_layout.addLayout(right_layout)

        self.location_list = LocationListWidget(self)
        right_layout.addWidget(self.location_list)

        self.location_list.setFixedSize(120, 150)
        self.location_list.itemDoubleClicked.connect(self._list_double_click_callback)

        return widget

    def _get_path_tab(self):
        """"""
        self.path_list = PathList()
        try:
            with open(setting.PATH_PATH, "r") as f:
                self.path_list = PathList.load(f)
        except Exception as e:
            LOGGER.warning(f"Failed to load path list: {e}")

        return PathEditWidget(self.path_list)

    def _list_double_click_callback(self, item: LocationItem):
        """Callback function for double click item

        Args:
            item (LocationItem): double clicked item
        """
        self.pos_x.le.setText(str(item.location.position.x))
        self.pos_y.le.setText(str(item.location.position.y))
        self.pos_z.le.setText(str(item.location.position.z))

    def _position_btn_click_callback(self, flag: Axis):
        """Position button callback function

        Args:
            flag (Position.Flag): Pos to modify
        """
        match flag:
            case Axis.X:
                self.pos_x.le.setText(str(self._drone.state.position.x))
            case Axis.Y:
                self.pos_y.le.setText(str(self._drone.state.position.y))
            case Axis.Z:
                self.pos_z.le.setText(str(self._drone.state.position.z))

    def _add_btn_click_callback(self):
        if self._validate_input():
            pos = Position(
                float(self.pos_x.le.text()),
                float(self.pos_y.le.text()),
                float(self.pos_z.le.text())
            )
            location = Location(position=pos)
            dialog = LocationEditDialog(location=location, parent=self, mode=LocationEditDialog.Mode.ADD)
            result = dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                self.location_list.addItem(dialog.location)

    def _validate_input(self) -> bool:
        """Check if the position is valid. `True` if valid. `False` otherwise.

        Returns:
            bool: `True` if valid. `False` otherwise.
        """
        try:
            float(self.pos_x.le.text())
            float(self.pos_y.le.text())
            float(self.pos_z.le.text())
            return True
        except ValueError:
            return False

    def reject(self) -> None:
        super().reject()

    def accept(self):
        if self.mode == self.Mode.POSITION:
            if self._validate_input():
                self.result = Position(
                    float(self.pos_x.le.text()),
                    float(self.pos_y.le.text()),
                    float(self.pos_z.le.text())
                )
            else:
                QMessageBox.warning(self, "Invalid input", "Invalid x, y, z position")
                return
        elif self.mode == self.Mode.PATH:
            cur_path = self._path_widget.get_current_path()
            if cur_path is None:
                QMessageBox.warning(self, "Invalid input", "No path selected")
                return
            self.result = cur_path

        super().accept()

    def save(self):
        index = self.tabs.currentIndex()
        if index == 0:
            if self._validate_input():
                self.position = Position(
                    float(self.pos_x.le.text()),
                    float(self.pos_y.le.text()),
                    float(self.pos_z.le.text())
                )
                LOCATIONS.save(new_location=self.location_list.locations)
                QMessageBox.information(self, "Success", "Location saved")
            else:
                QMessageBox.warning(self, "Invalid input", "Invalid x, y, z position")
        elif index == 1:
            try:
                with open(setting.PATH_PATH, "w") as f:
                    self.path_list.save(f)
                    QMessageBox.information(self, "Success", "Path saved")
            except Exception as e:
                QMessageBox.warning(self, "Failed to save path", f"Save Failed")
                LOGGER.debug(f"Failed to save path: {e}")

    def _get_tab_size(self, add_width: int = 0, add_height: int = 0) -> QSize:
        """Get the current tab size"""
        index = self.tabs.currentIndex()
        size: QSize = self.tabs.widget(index).sizeHint()
        size.setHeight(size.height() + add_height)
        size.setWidth(size.width() + add_width)
        return size

    def tab_change_cb(self, index):
        self.resize(self._get_tab_size(add_height=50))
        self.mode = self.Mode.POSITION if index == 0 else self.Mode.PATH


class PositionLabelEditSetWidget(QWidget):
    """Special group of widget for GoToDialog. It contain a label, line edit and
    a button
    """

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._setup_ui(label)

    def _setup_ui(self, label: str):
        layout = QHBoxLayout()

        self.setLayout(layout)

        layout.addWidget(QLabel(label))

        self.le = QLineEdit()
        self.le.setMaximumWidth(40)
        layout.addWidget(self.le)

        self.btn = QPushButton()
        self.btn.setIcon(Icon.get_icon(_Icon.CURRENT_LOCATION.value))
        layout.addWidget(self.btn)

        layout.addStretch()
