from enum import Enum, auto


class DroneUICallBack(Enum):
    """
    Callback for the drone
    """
    LBL_CONNECT_STATUS = auto()
    LBL_FLY_STATUS = auto()
    LBL_BATTERY_PERCENTAGE = auto()
