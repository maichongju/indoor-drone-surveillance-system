from __future__ import annotations

import random

from vispy.color import ColorArray

from general.enum import Enum


class Color(Enum):
    ORANGE = '#FFA500'
    PURPLE = '#800080'
    PINK = '#FFC0CB'
    LIME = '#00FF00'
    AQUA = '#00FFDD'
    RED = '#FF0000'
    GREEN = '#00FF00'
    BLUE = '#0000FF'
    DARK_SKY_BLUE = '#4D90FA'
    ANDROID_GREEN = '#A4C639'
    BEE_YELLOW = '#E9AB17'
    BRILLIANT_ROSE = '#F653A6'

    @property
    def hex(self) -> str:
        return self.value

    @property
    def RGB(self) -> tuple[int, int, int]:
        r = int(self.hex[1:3], 16)
        g = int(self.hex[3:5], 16)
        b = int(self.hex[5:7], 16)
        return r, g, b

    @staticmethod
    def get_random_color() -> Color:
        return random.choice(list(Color))


class VispyColor:
    @staticmethod
    def get_color(color: Color | str, opacity: float = 1.0) -> ColorArray:
        if isinstance(color, Color):
            return ColorArray(color=color.hex, alpha=opacity)
        return ColorArray(color=color, alpha=opacity)

    @staticmethod
    def get_random_color(opacity: float = 1.0) -> ColorArray:
        return VispyColor.get_color(Color.get_random_color(), opacity)
