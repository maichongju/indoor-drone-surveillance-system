from __future__ import annotations
from .firmware import DroneModel
from general.enum import Enum


manually_control_velocity = 0.2

auto_velocity = 0.2

auto_avoidance_velocity = 0.2

hover_correction_velocity = 0.02

yaw_rate = 360 / 10


# low voltage: Display warning message
# critical voltage: Land the drone
battery_setting = {
    DroneModel.BOLT: {
        'low_voltage': 7.0,
        'critical_voltage': 6.6

    },
    DroneModel.CRAZYFILE: {
        'low_voltage': 3.5,
        'critical_voltage': 3.2
    }
}


class BatterySetting(Enum):
    # low voltage, critical voltage, full voltage, empty voltage
    BOLT = 7.0, 6.6, 8.4, 6.0
    CRAZYFILE = 3.5, 3.2, 4.2, 3.0

    @staticmethod
    def get_setting(model: DroneModel) -> BatterySetting:
        if model == DroneModel.BOLT:
            return BatterySetting.BOLT
        else:
            return BatterySetting.CRAZYFILE

    @property
    def low_voltage(self) -> float:
        return self[0]

    @property
    def critical_voltage(self) -> float:
        return self[1]

    @property
    def full_voltage(self) -> float:
        return self[2]

    @property
    def empty_voltage(self) -> float:
        return self[3]
