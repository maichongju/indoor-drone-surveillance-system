from __future__ import annotations

from enum import Enum

from PyQt6.QtGui import QIcon

from log.logger import LOGGER
from .widget.utils import is_icon_valid


class Icon(Enum):
    IMAGE_ERROR = './ui/icons/image_error.png'
    RED_DOT = './ui/icons/red_dot.png'
    YELLOW_DOT = './ui/icons/yellow_dot.png'
    BLUE_DOR = './ui/icons/blue_dot.png'
    GREEN_DOT = './ui/icons/green_dot.png'
    NO_SIGNAL = './ui/icons/no_signal.png'
    PLANE = './ui/icons/plane.png'
    PLANE_LANDING = './ui/icons/plane_landing.png'
    PLANE_TAKING_OFF = './ui/icons/plane_taking_off.png'
    HOME = './ui/icons/home.png'
    UP_ARROW = './ui/icons/up_arrow.png'
    DOWN_ARROW = './ui/icons/down_arrow.png'
    LEFT_ARROW = './ui/icons/left_arrow.png'
    RIGHT_ARROW = './ui/icons/right_arrow.png'
    TURN_DOWN_RIGHT = './ui/icons/turn_down_right.png'
    TURN_DOWN_LEFT = './ui/icons/turn_down_left.png'
    SETTING_WHEEL = './ui/icons/setting_wheel.png'
    DOWNLOAD = './ui/icons/download.png'
    DESTINATION = './ui/icons/destination.png'
    STOP_SIGN = './ui/icons/stop_sign.png'
    EDIT = './ui/icons/edit.png'
    MINUS_SIGN = './ui/icons/minus_sign.png'
    PLUS_SIGN = './ui/icons/plus_sign.png'
    DISKETTE = './ui/icons/diskette.png'

    @staticmethod
    def get_icon(icon: Icon):
        """Return the icon of the icon

        Args:
            icon (Icon): icon path
        """
        if not is_icon_valid(icon.value):
            LOGGER.warning(f"[UI] {icon.value} is invalid")
            return QIcon(Icon.IMAGE_ERROR.value)
        return QIcon(icon.value)

    @staticmethod
    def get_pixmap(icon: Icon, size: tuple = (16, 16)):
        """Return the pixmap of the icon

        Args:
            icon (Icon): icon path
            size (tuple): image size. Default to (16,16)
        """
        return Icon.get_icon(icon).pixmap(size[0], size[1])
