from enum import Enum

import cv2
import numpy as np
from PyQt6.QtCore import QObject
from PyQt6.QtCore import QSize
from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QIcon
from PyQt6.QtGui import QImage
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QBoxLayout
from PyQt6.QtWidgets import QFrame
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QProgressBar
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget, QInputDialog, QMessageBox, QGroupBox

from general.enum import IntEnum
from general.utils import Position
from hub.drone import Drone
from hub.path import Path, PathList
from log.logger import LOGGER
from ml.objectdetection import Result
from . import Location
from .canvas import Canvas3DVispy, VispyPath
from .dialog.locationdialog import LocationEditDialog
from .list import PathDetailsListWidget, PathListWidget, LocationItem
from .utils import is_icon_valid
from ..icon import Icon

VIDEO_SIZE = (640, 480)


class _Icon(Enum):
    ONLINE = Icon.GREEN_DOT
    OFFLINE = Icon.RED_DOT
    NO_SIGNAL = Icon.NO_SIGNAL
    CURRENT_LOCATION = Icon.DOWNLOAD
    ADD = Icon.PLUS_SIGN
    REMOVE = Icon.MINUS_SIGN
    SAVE = Icon.DISKETTE
    UP = Icon.UP_ARROW
    DOWN = Icon.DOWN_ARROW


# https://stackoverflow.com/questions/10533838/displaying-a-standard-icon-and-text-in-qlabel


class IconLabel(QWidget):
    icon_size = QSize(16, 16)

    def __init__(self, text: str,
                 qicon: str | Icon | None = None,
                 icon_location: Location = Location.START,
                 final_stretch: bool = True
                 ):
        """A label with an icon. It can work with normal QIcon or qAwesomeIcon. If any of 
        those are invalid, it will use the missing icon. If both provided, QIcon will be used.

        Args:
            text (str): text to be displayed
            qicon (str | None, optional): qticon. Defaults to None.
            aicon (str | None, optional): qAwesomeIcon. Defaults to None.
            icon_location (Location, optional): icon location. Defaults to Location.START
            final_stretch (bool, optional): stretch. Defaults to True.
        """
        super().__init__()
        layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        if icon_location not in [Location.START, Location.END]:
            icon_location = Location.START

        icon = None

        if isinstance(qicon, Icon):
            qicon = qicon.value

        if (is_icon_valid(qicon)):
            icon = QIcon(qicon).pixmap(self.icon_size)
        else:
            LOGGER.warning(f"[UI] {qicon} is invalid")

        self._text = QLabel(text)
        self._icon = QLabel()
        self._icon.setPixmap(icon) if icon is not None else None

        if icon_location == Location.START:
            layout.addWidget(self._icon)
            layout.addWidget(self._text)
        else:
            layout.addWidget(self._text)
            layout.addWidget(self._icon)

        if final_stretch:
            layout.addStretch()

        if icon_location == Location.END:
            layout.addWidget(self._text)
            layout.addWidget(self._icon)
        else:
            layout.addWidget(self._icon)
            layout.addWidget(self._text)

        if final_stretch:
            layout.addStretch()

    @property
    def text(self) -> str:
        return self._text.text()

    @text.setter
    def text(self, value: str):
        self._text.setText(value)

    @property
    def icon(self) -> QLabel:
        return self._icon

    @icon.setter
    def icon(self, value: str | Icon):
        if isinstance(value, Icon):
            value = value.value
        if (is_icon_valid(value)):
            icon = QIcon(value).pixmap(self.icon_size)
            self._icon.setPixmap(icon)
        else:
            LOGGER.warning(f"[UI] {value} is invalid")

    @property
    def icon_text(self) -> tuple:
        return self._icon, self._text.text()

    @icon_text.setter
    def icon_text(self, value: tuple):
        self.icon = value[0]
        self.text = value[1]


PROGRESSBAR_STYLE = """
QProgressBar {
    border: 1px solid grey;
    text-align: center;
    border-radius: 5px;
    font-size: 10px;
}

QProgressBar::chunk {
    background-color: #b3d9ff;
}
"""


class ThrustBar(QWidget):
    def __init__(self,
                 label: str = None,
                 tooltip: str = None,
                 location: Location = Location.UP,
                 label_center: bool = False,
                 parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

        self._lbl_text = QLabel(label)
        self._progress_bar = QProgressBar()

        self.setToolTip(tooltip)
        # Max int
        self._progress_bar.setMaximum(65535)
        self._progress_bar.setValue(0)

        if label_center:
            self._lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if location == Location.UP:
            layout.addWidget(self._lbl_text)
            layout.addWidget(self._progress_bar)
        else:
            layout.addWidget(self._progress_bar)
            layout.addWidget(self._lbl_text)

        self._progress_bar.setOrientation(Qt.Orientation.Vertical)
        self._progress_bar.setStyleSheet(PROGRESSBAR_STYLE)

    @property
    def lbl(self) -> QLabel:
        return self._lbl_text

    @property
    def pb(self) -> QProgressBar:
        return self._progress_bar

    @property
    def value(self) -> int:
        return self._progress_bar.value()

    @value.setter
    def value(self, value: int):
        self._progress_bar.setValue(value)


# https://stackoverflow.com/questions/44404349/pyqt-showing-video-stream-from-opencv


class _VideoStreamSignal(QObject):
    new_frame = pyqtSignal(np.ndarray)
    new_frame_od = pyqtSignal(Result)
    stream_ended = pyqtSignal()
    invalid_stream = pyqtSignal(str)
    connection_lost = pyqtSignal()
    stream_error = pyqtSignal(Exception)


class DroneStreamWidget(QFrame):
    """Video Stream Widget"""

    def __init__(self,
                 drone: Drone | None,
                 stream_resolution: tuple = VIDEO_SIZE,
                 display_name: bool = False,
                 name_location: Location = Location.DOWN,
                 style_sheet: str | None = None,
                 always_show_original_stream: bool = False
                 ):
        """Video Stream Widget. Display the video stream to the widget.

        Args:
            drone (Drone): Drone contain the video stream
            stream_resolution (tuple, optional): Video Resolution. Defaults to VIDEO_SIZE.
            display_name (bool, optional): Display drone name or not. Defaults to False.
            name_location (Location, optional): Location of drone name. Only allow up or down. Defaults to Location.DOWN.
            style_sheet (str | None, optional): Style Sheet. Defaults to None.
            object_detection
            always_show_original_stream (bool, optional): Always show the original stream. Defaults to False.
        """
        super().__init__()
        self.setObjectName("VideoStreamWidget")
        self._drone = drone
        self._stream_resolution = stream_resolution
        self._display_name = display_name
        self._name_location = name_location
        self._signals = _VideoStreamSignal()
        self._always_show_original_stream = always_show_original_stream
        if style_sheet is not None:
            self.setStyleSheet(style_sheet)
        self._setup_ui()
        self._setup_callbacks()

        self.is_visible = False

    def _setup_callbacks(self):
        if self._drone is None:
            return
        # Normal Frame
        self._drone.video_callbacks.new_frame.add_callback(
            self._signals.new_frame.emit)
        self._signals.new_frame.connect(self._update_stream_img)

        # Object Detection Frame
        self._drone.video_callbacks.new_frame_od_enabled.add_callback(
            self._signals.new_frame_od.emit)
        self._signals.new_frame_od.connect(self._update_stream_img)

        self._drone.video_callbacks.stream_ended.add_callback(
            self._signals.stream_ended.emit)
        # Image update
        self._signals.stream_ended.connect(self._reset_stream_img)

        # Invalid Stream Signal
        self._drone.video_callbacks.invalid_stream.add_callback(
            self._signals.invalid_stream.emit)

        # Connection Lost Signal
        self._drone.video_callbacks.connection_lost.add_callback(
            self._signals.connection_lost.emit)

        # Stream Error Signal
        self._drone.video_callbacks.stream_error.add_callback(
            self._signals.stream_error.emit)

    def _setup_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        if self._display_name:
            lbl_name = QLabel(self._drone.name)
            lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if self._name_location == Location.UP:
                main_layout.addWidget(lbl_name)

        # Stream Image. Use QLabel to display the image
        self.stream_img = QLabel()
        self.stream_img.setPixmap(Icon.get_pixmap(
            _Icon.NO_SIGNAL.value, (32, 32)))
        self.stream_img.setFixedSize(
            self._stream_resolution[0], self._stream_resolution[1])
        self.stream_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.stream_img)

        if self._display_name and self._name_location == Location.DOWN:
            main_layout.addWidget(lbl_name)

    def _reset_stream_img(self, *arg):
        self.stream_img.setPixmap(Icon.get_pixmap(
            _Icon.NO_SIGNAL.value, (32, 32)))

    @pyqtSlot(object)
    def _update_stream_img(self, result: np.ndarray | Result):
        """Update the stream image.

        Args:
            result (np.ndarray): image to be displayed
        """
        if not self.is_visible:
            return

        # Always show the original stream. But this frame is with od. Skip
        if self._always_show_original_stream and isinstance(result, Result):
            return

        #
        if not self._always_show_original_stream:
            if self._drone.object_detection and self._drone.object_detection_init and isinstance(result, np.ndarray):
                return

        if isinstance(result, Result):
            frame = result.frame
        else:
            frame = result

        rbgImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rbgImage.shape
        bytesPerLine = ch * w
        convertToQtFormat = QImage(
            rbgImage.data, w, h, bytesPerLine, QImage.Format.Format_RGB888)
        p = convertToQtFormat.scaled(
            self._stream_resolution[0], self._stream_resolution[1], Qt.AspectRatioMode.KeepAspectRatio)
        self.stream_img.setPixmap(QPixmap.fromImage(p))

    def set_visible(self, value: bool):
        self.is_visible = value


class PathEditWidget(QWidget):
    class _Mode(IntEnum):
        PATH = 0
        PATH_DETAIL = 1

    def __init__(self, path_list: PathList):
        super().__init__()

        self._path_list = path_list
        self.current_path = None
        self._path_list_cur_index = -1
        self._canvas_path: VispyPath | None = None

        self._setup_ui()
        self._set_enable_path_detail(False)

    def _setup_ui(self):
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        self._path_list_ui = self._get_path_list_ui()
        self._path_detail_ui = self._get_path_detail_ui()

        main_layout.addWidget(self._path_list_ui)
        main_layout.addWidget(self._path_detail_ui)

        self._canvas = Canvas3DVispy(size=(500, 300))

        main_layout.addWidget(self._canvas.native)

    def _get_path_list_ui(self) -> QGroupBox:
        gb_path_list = QGroupBox("Paths")

        gb_path_list_layout = QHBoxLayout()
        gb_path_list.setLayout(gb_path_list_layout)

        self.path_list = PathListWidget(self._path_list)
        gb_path_list_layout.addWidget(self.path_list)
        self.path_list.setMaximumWidth(100)
        self.path_list.itemDoubleClicked.connect(lambda path: self._display_path(path.path))

        paths_btn_layout = QVBoxLayout()
        gb_path_list_layout.addLayout(paths_btn_layout)

        btn_add_path = QPushButton("")
        btn_add_path.setIcon(Icon.get_icon(_Icon.ADD.value))
        btn_add_path.clicked.connect(lambda: self._btn_add_on_click(self._Mode.PATH))
        paths_btn_layout.addWidget(btn_add_path)

        btn_remove_path = QPushButton("")
        btn_remove_path.setIcon(Icon.get_icon(_Icon.REMOVE.value))
        btn_remove_path.clicked.connect(lambda: self._btn_remove_on_click(self._Mode.PATH))
        paths_btn_layout.addWidget(btn_remove_path)

        paths_btn_layout.addStretch()

        return gb_path_list

    def _get_path_detail_ui(self) -> QGroupBox:
        gb_path_detail = QGroupBox("Path Detail")

        gb_path_detail_layout = QHBoxLayout()
        gb_path_detail.setLayout(gb_path_detail_layout)

        self.path_detail = PathDetailsListWidget()
        gb_path_detail_layout.addWidget(self.path_detail)
        self.path_detail.setMaximumWidth(150)
        self.path_detail.itemDoubleClicked.connect(lambda item: self._edit_location(item))
        self.path_detail.itemClicked.connect(lambda cur: self._highlight_pos(cur.location.position))

        path_detail_btn_layout = QVBoxLayout()
        gb_path_detail_layout.addLayout(path_detail_btn_layout)

        btn_add_path_detail = QPushButton("")
        btn_add_path_detail.setIcon(Icon.get_icon(_Icon.ADD.value))
        btn_add_path_detail.clicked.connect(lambda: self._btn_add_on_click(self._Mode.PATH_DETAIL))
        path_detail_btn_layout.addWidget(btn_add_path_detail)

        btn_remove_path_detail = QPushButton("")
        btn_remove_path_detail.setIcon(Icon.get_icon(_Icon.REMOVE.value))
        btn_remove_path_detail.clicked.connect(lambda: self._btn_remove_on_click(self._Mode.PATH_DETAIL))
        path_detail_btn_layout.addWidget(btn_remove_path_detail)

        btn_move_up = QPushButton("")
        btn_move_up.setIcon(Icon.get_icon(_Icon.UP.value))
        btn_move_up.clicked.connect(lambda: self.move_path_position("up"))
        path_detail_btn_layout.addWidget(btn_move_up)

        btn_move_down = QPushButton("")
        btn_move_down.setIcon(Icon.get_icon(_Icon.DOWN.value))
        btn_move_down.clicked.connect(lambda: self.move_path_position("down"))
        path_detail_btn_layout.addWidget(btn_move_down)

        btn_save_path_detail = QPushButton("")
        btn_save_path_detail.setIcon(Icon.get_icon(_Icon.SAVE.value))
        btn_save_path_detail.clicked.connect(self._btn_save_path_detail_on_click)
        path_detail_btn_layout.addWidget(btn_save_path_detail)

        path_detail_btn_layout.addStretch()

        return gb_path_detail

    def _display_path(self, path: Path):
        """
        Helper function that will set up everything needs to display a path. This will also
        display the path on the canvas.
        """
        if self._path_list_cur_index != -1 and self.path_detail.is_updated:
            reply = QMessageBox.question(self, "Unsaved Changes",
                                         "You have unsaved changes, do you want to save them?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Yes:
                self._btn_save_path_detail_on_click()
            elif reply == QMessageBox.StandardButton.Cancel:
                self.path_detail.setCurrentRow(self._path_list_cur_index)
                return
        self._set_enable_path_detail(True)
        self._path_detail_ui.setTitle(f"Path Detail - {path.name}")
        self.path_detail.load(path)
        self._path_list_cur_index = self.path_list.currentRow()
        self._canvas_draw_path(path)
        self._canvas_path.clear_highlight_pos()

    def _canvas_draw_path(self, path: Path):
        """
        Helper function that will draw the path on the canvas. this will also remove the highlight point.
        """
        self._canvas_path = self._canvas.plot_path(path, vispy_path=self._canvas_path)

    def _set_enable_path_detail(self, enable: bool):
        self._path_detail_ui.setEnabled(enable)

    def _btn_add_on_click(self, mode: _Mode):
        if mode == self._Mode.PATH:
            path_name, ok = QInputDialog.getText(self, "Create New Path", "Enter the name of the path")
            if ok:
                if self.path_list.paths.name_exists(path_name):
                    QMessageBox.critical(self, "Error", "A path with this name already exists.")
                else:
                    path = Path(path_name)
                    self.path_list.paths.add_path(path)
                    self.path_list.addItem(path)
                    self.path_list.setCurrentRow(self.path_list.count() - 1)
                    self._display_path(path)
        elif mode == self._Mode.PATH_DETAIL:
            dialog = LocationEditDialog(parent=self, mode=LocationEditDialog.Mode.ADD, show_name=False)
            if dialog.exec():  # New path is created
                pos = dialog.location.position
                if self.path_detail.currentRow() == -1:
                    self.path_detail.addItem(pos)
                    self.path_detail.setCurrentRow(0)
                else:
                    self.path_detail.insertItem(self.path_detail.currentRow(), pos)
                    self.path_detail.setCurrentRow(self.path_detail.currentRow() - 1)

                self._set_path_detail_is_updated(True)
                self._update_path_detail_canvas()

    def _highlight_pos(self, pos: Position):
        if self._canvas_path is not None:
            self._canvas_path.set_highlight_pos(pos)

    def _update_path_detail_canvas(self):
        """
        Trigger a redrawn of the path on the canvas.
        """
        if self._canvas_path is None:
            return  # No path is currently displayed

        active_pos = None
        if self.path_detail.currentRow() != -1:
            active_pos = self.path_detail.currentItem().location.position  # type: ignore
        else:  # No active position
            self._canvas_path.clear_highlight_pos()

        self._canvas_draw_path(self.path_detail.temp_path)

        # Draw the active position
        if active_pos is not None:
            self._canvas_path.set_highlight_pos(active_pos)
        else:
            self._canvas_path.clear_highlight_pos()

    def _set_path_detail_is_updated(self, is_updated: bool):
        self.path_detail.is_updated = is_updated
        if is_updated:
            self._path_detail_ui.setTitle(f"Path Detail - {self.path_detail.path.name} *")
        else:
            self._path_detail_ui.setTitle(f"Path Detail - {self.path_detail.path.name}")

    def _btn_remove_on_click(self, mode: _Mode):
        if mode == self._Mode.PATH:
            if self.path_list.currentRow() == -1:
                return
            reply = QMessageBox.question(self, "Remove Path",
                                         f"Are you sure you want to remove this path ({self.path_list.currentItem().path.name})?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                current_index = self.path_list.currentRow()
                self.path_list.paths.remove_path_by_index(current_index)
                self.path_list.takeItem(current_index)
                if self.path_list.count() != 0:
                    if current_index == self.path_list.count():
                        current_index -= 1
                else:
                    current_index = -1
                self.path_list.setCurrentRow(current_index)
                if current_index != -1:
                    self._display_path(self.path_list.currentItem().path)
                else:
                    self._set_enable_path_detail(False)
                    self.clear_canvas()
                    self.path_detail.clear()
                    self._path_detail_ui.setTitle("Path Detail")
                    self._path_detail_ui.setEnabled(False)

        elif mode == self._Mode.PATH_DETAIL:
            if self.path_detail.currentRow() == -1:
                return
            current_index = self.path_detail.currentRow()
            self.path_detail.takeItem(current_index)
            self._update_path_detail_canvas()
            self._set_path_detail_is_updated(True)

    def clear_canvas(self):
        if self._canvas_path is not None:
            self._canvas_path.clear()
            self._canvas_path = None

    def _edit_location(self, item: LocationItem):
        dialog = LocationEditDialog(location=item.location, parent=self, show_name=False)
        if dialog.exec():
            self.path_detail.update_pos_at_index(self.path_detail.currentRow(), dialog.location.position)
            self._path_detail_ui.setTitle(f"Path Detail - {self.path_detail.path.name} *")
            self._update_path_detail_canvas()

    def move_path_position(self, direction: str):
        if direction == "up":
            if self.path_detail.currentRow() == -1 or self.path_detail.currentRow() == 0:
                return
            current_index = self.path_detail.currentRow()
            self.path_detail.swap_item(current_index, current_index - 1)
            self.path_detail.setCurrentRow(current_index - 1)
        elif direction == "down":
            if self.path_detail.currentRow() == -1 or self.path_detail.currentRow() == self.path_detail.count() - 1:
                return
            current_index = self.path_detail.currentRow()
            self.path_detail.swap_item(current_index, current_index + 1)
            self.path_detail.setCurrentRow(current_index + 1)

        self._set_path_detail_is_updated(True)
        self._update_path_detail_canvas()

    def _btn_save_path_detail_on_click(self):
        self.path_detail.apply_change()
        self._set_path_detail_is_updated(False)

    def get_current_path(self) -> Path | None:
        if self.path_list.currentRow() == -1:
            return None
        return self.path_list.currentItem().path
