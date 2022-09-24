from enum import Enum, auto
from PyQt6.QtCore import QSize
from PyQt6.QtGui import QIcon

from PyQt6.QtWidgets import QLabel


class Threshold(Enum):
    LESS_EQUAL_THAN = auto()
    GREATER_EQUAL_THAN = auto()
    LESS_THAN = auto()
    GREATER_THAN = auto()


class Style(Enum):
    """QLabel Style name. Same as css
    https://www.w3schools.com/cssref/

    Args:
        Enum (_type_): _description_
    """
    BACKGROUND_COLOR = "background-color"
    TEXT_COLOR = "color"
    TEXT_WEIGHT = "font-weight"


class StylePreset(Enum):
    """QLabel Style preset.
    """

    """text: red"""
    WARNING_TEXT = (Style.TEXT_COLOR, "red"),

    """text: red, bold """
    WARNING_TEXT_BOLD = (Style.TEXT_COLOR, "red"), \
        (Style.TEXT_WEIGHT, "bold")
    """text: black, normal"""
    DEFAULT_TEXT = (Style.TEXT_COLOR, "black"), \
                   (Style.TEXT_WEIGHT, "normal")


def set_label_style(label: QLabel, preset: StylePreset = None, styles: dict = {}) -> None:
    """Set the label to the given style. If preset is given it will be used and igonre
    the styles argument. If preset is not given, styles will be used.

    Args:
        label (QLabel): Label that need to be styled
        preset (QLabelStylePreset, optional): Preset style. Defaults to None.
    """

    style_str = ""
    if preset is not None and isinstance(preset, StylePreset):
        for style, val in preset.value:
            style_str += f"{style.value}: {val};"

        label.setStyleSheet(style_str)
    # Do nothing if style is not provided
    if len(styles) == 0:
        return

    for style, val in styles.items():
        style_str += f"{style.value}: {val};"
    label.setStyleSheet(style_str)


def set_label_style_threshold(
    label: QLabel,
    value: float,
    threshold: float,
    threshold_type: Threshold = Threshold.LESS_EQUAL_THAN,
    normal_style: StylePreset | tuple = StylePreset.DEFAULT_TEXT,
    beyond_threshold_style: StylePreset | tuple = StylePreset.WARNING_TEXT
) -> None:
    """if the value is lower than the threshold, then the `lower_threshold_style` 
    will be apply to the text. Otherwise the `normal_style` will be applied. 

    Args:
        label (QLabel): label need to be apply style
        value (float): value to be checked
        threshold (float): threshold value
        normal_style (QLabelStylePreset | tuple, optional): normal style. Defaults to QLabelStylePreset.DEFAULT_TEXT.
        lower_threshold_style (QLabelStylePreset | tuple, optional): Warning style. Defaults to QLabelStylePreset.WARNING_TEXT.
    """
    match threshold_type:
        case Threshold.LESS_EQUAL_THAN:
            if value <= threshold:
                set_label_style(label, beyond_threshold_style)
            else:
                set_label_style(label, normal_style)
        case Threshold.GREATER_EQUAL_THAN:
            if value >= threshold:
                set_label_style(label, beyond_threshold_style)
            else:
                set_label_style(label, normal_style)
        case Threshold.LESS_THAN:
            if value < threshold:
                set_label_style(label, beyond_threshold_style)
            else:
                set_label_style(label, normal_style)
        case Threshold.GREATER_THAN:
            if value > threshold:
                set_label_style(label, beyond_threshold_style)
            else:
                set_label_style(label, normal_style)


def is_icon_valid(path: str) -> bool:
    """Check if the icon is valid.

    Args:
        path (str): path to the icon

    Returns:
        bool: True if valid, False otherwise
    """
    return not QIcon(path).pixmap(QSize(16, 16)).isNull()


def callback_ignored_error(cb, *args):
    """Special callback for video callbacks. For UI callback. When the program ends, all the ui will be destroy
    therefor the signal does not exist. That will cause an `AttributeError` exception. This error 
    is expected and can be ignored. 

    Args:
        cb (function): _description_
    """
    try:
        cb(*args)
    except:
        pass
