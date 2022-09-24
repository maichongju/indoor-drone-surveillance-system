from linecache import lazycache
import logging
from threading import Thread
from enum import Enum
import time

from hub.drone import Drone
from ..icon import Icon
from ml.objectdetection import Result

import cv2
import numpy as np

from PyQt6.QtCore import QSize
from PyQt6.QtGui import QImage
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QWidget
from PyQt6.QtWidgets import QProgressBar
from PyQt6.QtWidgets import QBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtWidgets import QPushButton


from PyQt6.QtWidgets import QFrame
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtCore import QObject
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtCore import Qt

from . import Location
from .utils import is_icon_valid

from log.logger import LOGGER

VIDEO_SIZE = (640, 480)


class _Icon(Enum):
    ONLINE = Icon.GREEN_DOT
    OFFLINE = Icon.RED_DOT
    NO_SIGNAL = Icon.NO_SIGNAL
    CURRENT_LOCATION = Icon.DOWNLOAD


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


class PositionLabelEditSetWidget(QWidget):
    """Special group of widget for GoToDialog. It contain a label, line edit and 
    a button
    """
    def __init__(self, label:str, parent = None):
        super().__init__(parent)
        self._setup_ui(label)
        
    def _setup_ui(self, label:str):
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
        
    