import logging
from dataclasses import dataclass, field

import jsonpickle

from general.enum import Enum
from general.utils import Position

LOGGER_LEVEL_DRONE = logging.INFO + 5


class LogTocType(Enum):
    """
    Log TOC type. See cflib.crazyflie.log.LogTocElement.
    """
    UINT8 = 'uint8_t'
    INT8 = 'int8_t'
    UINT16 = 'uint16_t'
    INT16 = 'int16_t'
    UINT32 = 'uint32_t'
    INT32 = 'int32_t'
    FP16 = 'FP16'
    FLOAT = 'float'


BATTERY_STATE = ['Battery', 'Charging', 'Charged', ' Low power', 'Shutdown']

LOCO_MODE = ['TWR', 'TDoA2', 'TDoA3']


def get_battery_state_name(x): return BATTERY_STATE[x]


def get_loco_mode_name(x): return LOCO_MODE[x - 1]


class LogVariable(Enum):
    """
    Logging variables name and type for the Crazyflie.
    Base on https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/api/logs/
    """

    # Core function
    CORE_ROLL = 'stateEstimate.roll', LogTocType.FLOAT
    CORE_PITCH = 'stateEstimate.pitch', LogTocType.FLOAT
    CORE_YAW = 'stateEstimate.yaw', LogTocType.FLOAT,
    CORE_THRUST = 'stabilizer.thrust', LogTocType.FLOAT

    # Power Management
    POWER_MANAGER_BATTERY_LEVEL = 'pm.batteryLevel', LogTocType.UINT8
    POWER_MANAGER_BATTERY_VOLTAGE = 'pm.vbat', LogTocType.FLOAT
    POWER_MANAGER_BATTERY_STATE = 'pm.state', LogTocType.UINT8

    # loco
    POSITION_X = 'stateEstimate.x', LogTocType.FLOAT
    POSITION_Y = 'stateEstimate.y', LogTocType.FLOAT
    POSITION_Z = 'stateEstimate.z', LogTocType.FLOAT

    # Flow Deck
    FLOW_DECK_MOTION = 'motion.motion', LogTocType.UINT8
    FLOW_DECK_DELTA_X = 'motion.deltaX', LogTocType.INT16
    FLOW_DECK_DELTA_Y = 'motion.deltaY', LogTocType.INT16
    FLOW_DECK_MEASURE_DX = 'kalman_pred.measNX', LogTocType.FLOAT
    FLOW_DECK_MEASURE_DY = 'kalman_pred.measNY', LogTocType.FLOAT
    FLOW_DECK_PRED_DX = 'kalman_pred.predNX', LogTocType.FLOAT
    FLOW_DECK_PRED_DY = 'kalman_pred.predNY', LogTocType.FLOAT

    # Multi Range Deck
    # Unit are in mm, if is grater than 8000 it is considered out of range
    MULTI_RANGER_FRONT = 'range.front', LogTocType.UINT16
    MULTI_RANGER_REAR = 'range.back', LogTocType.UINT16
    MULTI_RANGER_LEFT = 'range.left', LogTocType.UINT16
    MULTI_RANGER_RIGHT = 'range.right', LogTocType.UINT16
    MULTI_RANGER_UP = 'range.up', LogTocType.UINT16
    MULTI_RANGER_DOWN = 'range.zrange', LogTocType.UINT16

    # Motor
    MOTOR_M1 = 'motor.m1', LogTocType.UINT16
    MOTOR_M2 = 'motor.m2', LogTocType.UINT16
    MOTOR_M3 = 'motor.m3', LogTocType.UINT16
    MOTOR_M4 = 'motor.m4', LogTocType.UINT16

    # Loco Position
    LOCO_MODE = 'loco.mode', LogTocType.UINT8

    @property
    def name(self) -> str:
        """
        Return the name of the variable.
        """
        return self.value[0]

    @property
    def type(self) -> LogTocType:
        """
        Return the type of the variable.
        """
        return self.value[1]

    @classmethod
    def get_multi_ranger(cls) -> list:
        """Generate list of multi ranger variables

        Returns:
            _type_: _description_
        """
        return [
            cls.MULTI_RANGER_FRONT,
            cls.MULTI_RANGER_REAR,
            cls.MULTI_RANGER_LEFT,
            cls.MULTI_RANGER_RIGHT,
            cls.MULTI_RANGER_UP
        ]


MAX_DRONE_INFO_CACHE = 10
MAX_RANGE_OBSERVATION = 2000  # mm

MULTI_RANGER_NAME = [
    LogVariable.MULTI_RANGER_FRONT.value[0],
    LogVariable.MULTI_RANGER_REAR.value[0],
    LogVariable.MULTI_RANGER_UP.value[0],
    LogVariable.MULTI_RANGER_LEFT.value[0],
    LogVariable.MULTI_RANGER_RIGHT.value[0],
    LogVariable.MULTI_RANGER_DOWN.value[0],
]

YAW_THRESHOLD = 178


@dataclass
class DroneInfo:
    """Data class that store all the state of the drone. Store in the `state`
    attribute. The state is a dictionary.
    """
    state: dict = field(default_factory=dict)
    _cache_state: dict = field(default_factory=lambda: {
        # LogVariable.POSITION_X.value[0]: List(1),
        # LogVariable.POSITION_Y.value[0]: List(1),
        # LogVariable.POSITION_Z.value[0]: List(1),

    })

    def update(self, data: dict) -> None:
        """Update the state with the new data.

        Args:
            data: new data
        """
        state_except = [
            LogVariable.POWER_MANAGER_BATTERY_STATE.value[0],
            LogVariable.LOCO_MODE.value[0]
        ]

        for key, value in data.items():
            # if key in state_except:
            #     self.state[key] = value
            #     continue
            #
            if key in MULTI_RANGER_NAME and value > MAX_RANGE_OBSERVATION:
                value = MAX_RANGE_OBSERVATION
            #
            # if key not in self._cache_state:
            #     self._cache_state[key] = List(1)  # Buffer size
            # else:
            #     # Check special value for yaw
            #     if key == LogVariable.CORE_YAW.value[0]:
            #         if abs(value) > YAW_THRESHOLD:
            #             if len(self._cache_state[key]) > 0:
            #                 if not is_same_sign(value, self._cache_state[key][-1]):
            #                     self._cache_state[key].clear()
            #
            #     self._cache_state[key].append(value)
            #
            # self.state[key] = self._cache_state[key].avg()
            self.state[key] = value if not isinstance(value, float) else round(value, 3)

    def _mm_to_m(self, mm: float | None) -> float | None:
        """Convert mm to cm

        Args:
            mm: mm to convert

        Returns:
            float: cm
        """
        if mm is None:
            return None
        return mm / 1000

    def to_json(self, indent: int | None = None) -> str:
        """Convert the object to json

        Returns:
            str: Drone info in json format 
        """
        return jsonpickle.encode(self.__getstate__(), unpicklable=False, indent=indent)

    def to_csv_header(self) -> str:
        """Get the csv header

        Returns:
            str: csv header
        """
        return ','.join(self.state.keys())

    def to_csv(self) -> str:
        """Get the csv value

        Returns:
            str: csv value
        """
        return ','.join([str(value) for value in self.state.values()])

    def __getstate__(self) -> dict:
        exclude_prop = ['update', 'to_json', 'state', '_cache_state']
        json_dict = {}
        for prop in dir(self):
            if prop.startswith('_') or prop in exclude_prop:
                continue
            json_dict[prop] = getattr(self, prop)
        return json_dict

    @property
    def battery_level(self) -> int:
        return int(self.state.get(LogVariable.POWER_MANAGER_BATTERY_LEVEL.value[0], None))

    @property
    def battery_voltage(self) -> float:
        return self.state.get(LogVariable.POWER_MANAGER_BATTERY_VOLTAGE.value[0], None)

    @property
    def battery_state(self) -> int:
        return self.state.get(LogVariable.POWER_MANAGER_BATTERY_STATE.value[0], None)

    @property
    def loco_mode(self) -> int:
        return self.state.get(LogVariable.LOCO_MODE.value[0], None)

    @property
    def roll(self) -> float:
        return self.state.get(LogVariable.CORE_ROLL.value[0], None)

    @property
    def pitch(self) -> float:
        return self.state.get(LogVariable.CORE_PITCH.value[0], None)

    @property
    def yaw(self) -> float:
        return round(self.state.get(LogVariable.CORE_YAW.value[0], None))

    @property
    def thrust(self) -> float:
        return self.state.get(LogVariable.CORE_THRUST.value[0], None)

    @property
    def front_distance(self) -> float:
        """ distance in m"""
        return self._mm_to_m(self.state.get(LogVariable.MULTI_RANGER_FRONT.value[0], None))

    @property
    def rear_distance(self) -> float:
        """ distance in m"""
        return self._mm_to_m(self.state.get(LogVariable.MULTI_RANGER_REAR.value[0], None))

    @property
    def up_distance(self) -> float:
        """ distance in m"""
        return self._mm_to_m(self.state.get(LogVariable.MULTI_RANGER_UP.value[0], None))

    @property
    def left_distance(self) -> float:
        """ distance in m"""
        return self._mm_to_m(self.state.get(LogVariable.MULTI_RANGER_LEFT.value[0], None))

    @property
    def right_distance(self) -> float:
        """ distance in m"""
        return self._mm_to_m(self.state.get(LogVariable.MULTI_RANGER_RIGHT.value[0], None))

    @property
    def height(self) -> float:
        """ distance in m"""
        return self._mm_to_m(self.state.get(LogVariable.MULTI_RANGER_DOWN.value[0], None))

    @property
    def thrust_m1(self) -> int:
        return int(self.state.get(LogVariable.MOTOR_M1.value[0], None))

    @property
    def thrust_m2(self) -> int:
        return int(self.state.get(LogVariable.MOTOR_M2.value[0], None))

    @property
    def thrust_m3(self) -> int:
        return int(self.state.get(LogVariable.MOTOR_M3.value[0], None))

    @property
    def thrust_m4(self) -> int:
        return int(self.state.get(LogVariable.MOTOR_M4.value[0], None))

    @property
    def position(self) -> Position:
        return Position(
            self.state.get(LogVariable.POSITION_X.value[0], 0),
            self.state.get(LogVariable.POSITION_Y.value[0], 0),
            self.state.get(LogVariable.POSITION_Z.value[0], 0)
        )


class DroneExtraLog(str, Enum):
    MODE = 'mode'
    HOLD_POS = 'hold_pos'
    HOLD_CORRECTION = 'hold_correction'
    CORRECTION = 'correction'
    AXIS_CHANGE_TO = 'axis_change_to'
    CURRENT_AXIS = 'current_axis'
    DISTANCE_TO_TARGET = 'distance_to_target'
    THRUST_PERCENT = 'thrust_percent'
    MAINTAIN_DIRECTION_OFFSET = 'maintain_direction_offset'
    GO_TO_MODE = 'go_to_mode'
