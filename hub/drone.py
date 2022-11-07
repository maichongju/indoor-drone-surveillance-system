from __future__ import annotations

import math
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from logging import Logger
from queue import Empty, Queue
from threading import Event, Thread

import jsonpickle
# Crazyflie lib
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils.power_switch import PowerSwitch
from cflib.utils.uri_helper import uri_from_env
from sympy import Line, Point

from config.config import ConfigKey
from general.callbacks import Caller, VariableCallback
from general.cflib import CFParameter
from general.debug import get_dump_flight_data_file
from general.enum import IntEnum, auto
from general.list import List
from general.singleton import SINGLETON
from general.utils import (Axis, AxisDirection, Direction, Position, GDirection,
                           has_dongle, percentage_cal, rotate_axis_coord,
                           point_relevant_location_yaw, point_relevant_location,
                           get_yaw_from_axis_direction, round_up, get_projection_point)
from hub.dronesetting import *
from hub.firmware import Firmware
from hub.stream import StreamCallBacks, VideoStream
from log import DroneInfo, LogVariable
from log.dronelogger import (BatteryLogger, CoreLogger, MotorThrustLogger, MultiRangerLogger,
                             PositionLogger)
from log.logger import LOGGER
from .path import Path


class DroneException(Exception):
    pass


class FlyMode(Enum):
    NORMAL = 'NORMAL'
    HOVER = 'HOVER'
    MOVING = 'MOVING'
    # Moving to a position
    TARGET = 'TARGET'
    TAKE_OFF = 'TAKE_OFF'
    LAND = 'LAND'

    @staticmethod
    def get_by_name(name: str):
        for mode in FlyMode:
            if mode.name.upper() == name.upper():
                return mode
        raise ValueError("Unknown Fly Mode: {}".format(name))

    def __getstate__(self):
        return self.name


class FlyControlMode(Enum):
    MANUALLY = 'MANUALLY'
    AUTO = 'AUTO'

    def __getstate__(self):
        return self.name


class FlyStatus(IntEnum):
    LANDED = 0
    LANDING = 1
    TAKING_OFF = 2
    FLYING = 3

    def __getstate__(self):
        return self.name


class DronePowerAction(Enum):
    POWER_OFF = auto()
    REBOOT = auto()


class FlyCommandManually(IntEnum):
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4
    FORWARD = 5
    BACKWARD = 6
    YAW_LEFT = 7
    YAW_RIGHT = 8


@dataclass
class DroneDecks:
    z_flow: bool = False
    loco_position: bool = False
    multi_ranger: bool = False


@dataclass
class Motion:
    """Movement class, unit is m/s
    """
    vx: float = 0
    vy: float = 0
    vz: float = 0
    yaw: float = 0

    def reset(self):
        self.vx = 0
        self.vy = 0
        self.vz = 0
        self.yaw = 0

    @classmethod
    def forward(cls, velocity):
        return cls(velocity, 0, 0, 0)

    @classmethod
    def backward(cls, velocity):
        return cls(-velocity, 0, 0, 0)

    @classmethod
    def left(cls, velocity):
        return cls(0, velocity, 0, 0)

    @classmethod
    def right(cls, velocity):
        return cls(0, -velocity, 0, 0)

    @classmethod
    def up(cls, velocity):
        return cls(0, 0, velocity, 0)

    @classmethod
    def down(cls, velocity):
        return cls(0, 0, -velocity, 0)

    @classmethod
    def yaw_left(cls, velocity):
        return cls(0, 0, 0, -velocity)

    @classmethod
    def yaw_right(cls, velocity):
        return cls(0, 0, 0, velocity)

    @classmethod
    def zero(cls):
        return cls(0, 0, 0, 0)

    def __add__(self, other: Motion | Position):
        """Override `+` operation
        """
        if not isinstance(other, Motion) and not isinstance(other, Position):
            raise TypeError(
                'DroneMovement can only be added with DroneMovement or Position')

        return Motion(
            self.vx + other.vx,
            self.vy + other.vy,
            self.vz + other.vz,
            self.yaw +
            (other.yaw if isinstance(other, Motion) else 0)
        )

    def __sub__(self, other: Motion | Position):
        """Override `-` operation
        """
        if not isinstance(other, Motion) and not isinstance(other, Position):
            raise TypeError(
                'DroneMovement can only be subtracted with DroneMovement or Position')

        return Motion(
            self.vx - other.vx,
            self.vy - other.vy,
            self.vz - other.vz,
            self.yaw -
            (other.yaw if isinstance(other, Motion) else 0)
        )

    def to_csv(self):
        return f"{self.vx:.3f},{self.vy:.3f},{self.vz:.3f},{self.yaw:.3f}"

    def __str__(self):
        return f"({self.vx:.3f}, {self.vy:.3f}, {self.vz:.3f}, {self.yaw:.3f})"


@dataclass
class DroneLoggerCallBacks:
    """Drone callbacks
    """
    # connection_lost: Callable | None = None
    # taking off, landed, flying, landing...
    drone_status_callback: Caller = field(default_factory=Caller, init=False)

    """Logger call back (UI)"""
    core_logger_callback: Caller = field(default_factory=Caller, init=False)

    multi_ranger_logger_callback: Caller = field(
        default_factory=Caller, init=False)

    motor_thrust_logger_callback: Caller = field(
        default_factory=Caller, init=False)

    position_logger_callback: Caller = field(
        default_factory=Caller, init=False)

    battery_logger_callback: Caller = field(default_factory=Caller, init=False)

    loco_logger_callback: Caller = field(default_factory=Caller, init=False)


@dataclass
class DroneWarning:
    low_voltage: bool = False


class Drone:

    def __init__(self,
                 name: str,
                 uri: str,
                 stream_url: str,
                 log_var: list[LogVariable] = None,
                 stream_resolution: tuple = (640, 480),
                 debug=False
                 ) -> None:
        """Constructor for the Drone class. Mean to intergrade with th GUI

        Args:
            name (str): name of the drone
            uri (str): drone uri
            stream (str): video stream address
            log_var (list[LogVariable]): list of log variables to be logged
            ui_callback (dict[DroneUICallBack, Callable] | None, optional): 
                list of ui callback. Defaults to None.
        """
        self._uri = uri_from_env(default=uri)
        self._name = name
        self._id = None
        self._log_var = log_var
        self._drone_info = DroneInfo()
        self._fly_mode = FlyMode.NORMAL
        self._scf = SyncCrazyflie(
            self._uri, cf=Crazyflie(rw_cache='./cache'))
        self._core_logger = None
        self.fly_control = FlyControl(self)
        self._debug = debug

        self.low_voltage_cb = Caller()
        self.onboard_low_voltage_cb = Caller()

        self._scf.cf.param.add_update_callback(
            group="deck", name="bcFlow2",
            cb=lambda _, value: self._drone_decks_event["z_flow"].set() if int(value) else None)
        self._scf.cf.param.add_update_callback(
            group="deck", name="bcDWM1000",
            cb=lambda _, value: self._drone_decks_event["loco_position"].set() if int(value) else None)
        self._scf.cf.param.add_update_callback(
            group="deck", name="bcMultiranger",
            cb=lambda _, value: self._drone_decks_event["multi_ranger"].set() if int(value) else None)

        self._scf.cf.param.add_update_callback(
            group="system", name='forceArm',
            cb=lambda _, value: LOGGER.debug(f"forceArm: {value}"))

        self._logger = {}

        self._drone_decks = DroneDecks()
        self._drone_decks_event = {
            "z_flow": Event(),
            "loco_position": Event(),
            "multi_ranger": Event()
        }
        self._logger_callbacks = DroneLoggerCallBacks()
        self._video_stream = VideoStream(
            stream_url, stream_resolution)

        # Take off and land callbacks
        self.fly_control.take_off_cb.add_callback(lambda: self._logger_callbacks.drone_status_callback.call(
            FlyStatus.FLYING))

        self._warning = DroneWarning()

        self.is_low_voltage = False

    def connect(self):
        """Open connection to the Crazyflie and set up the basic components of the drone. 
        Including which deck is connected. The function will block until all the information in received.

        Raises:
            DroneException: If connection is already open
        """

        # debugpy.debug_this_thread()

        def check_deck(deck: str, timeout=3):
            """Check if a deck event have been set

            Args:
                deck (str): deck name
                timeout (int, optional): timeout after number of seconds. Defaults to 5.
            """
            if deck == "z_flow":
                self._drone_decks.z_flow = self._drone_decks_event['z_flow'].wait(
                    timeout=timeout)
            elif deck == "loco_position":
                self._drone_decks.loco_position = self._drone_decks_event['loco_position'].wait(
                    timeout=timeout)
            elif deck == "multi_ranger":
                self._drone_decks.multi_ranger = self._drone_decks_event['multi_ranger'].wait(
                    timeout=timeout)

        try:
            if not has_dongle():
                raise DroneException("No dongle found")
            self._scf.open_link()
            self._scf.wait_for_params()

            # Set up deck checking thread
            z_flow_thread = Thread(target=check_deck, args=("z_flow",))
            loco_position_thread = Thread(
                target=check_deck, args=("loco_position",))
            multi_ranger_thread = Thread(
                target=check_deck, args=("multi_ranger",))

            z_flow_thread.start()
            loco_position_thread.start()
            multi_ranger_thread.start()

            # Flow deck join
            z_flow_thread.join()
            loco_position_thread.join()
            multi_ranger_thread.join()

            self._id = self._get_drone_id()
            self._firmware_version = self._get_firmware_version()
            self._model = Firmware.get_model(self._firmware_version)
            self._voltage_monitor_setting = battery_setting[self._model]

        except Exception as e:
            raise DroneException(str(e))

        self._logger_callbacks.battery_logger_callback.add_callback(
            self.voltage_monitor)
        self._set_logger()
        self._start_logger()
        self.fly_control.reset()
        self._display_connect_msg()

    def _get_drone_id(self):
        """Get the drone serial number
        """
        id = ''
        id += f"{int(self._scf.cf.param.get_value('cpu.id0')):x}"
        id += f"{int(self._scf.cf.param.get_value('cpu.id1')):x}"
        id += f"{int(self._scf.cf.param.get_value('cpu.id2')):x}"
        return id

    def _get_firmware_version(self):
        """Get the firmware version
        """
        version = f"{int(self._scf.cf.param.get_value('firmware.revision0')):x}"
        version += f"{int(self._scf.cf.param.get_value('firmware.revision1')):x}"
        return version

    def set_arm(self, value: bool = True):
        """ Set the force arm to the given value. This will block for 0.5 seconds to ensure
        it is actually armed
        """
        # Not allow to arm if the battery is at critical voltage
        if value and self.is_low_voltage:
            LOGGER.warning("Battery is at critical voltage")
            return
        value = 1 if value else 0
        self._scf.cf.param.set_value('system.forceArm', value)
        time.sleep(0.5)
        if value:
            LOGGER.drone(f'Drone {self._name} is armed. Please be careful!')

    def _set_logger(self):
        """Set up the logger for the drone. Because there is a size limit for each packet,
        need different logger for each functional
        """

        self._logger['core'] = CoreLogger(self._scf,
                                          drone_state=self._drone_info,
                                          callback=self.drone_callbacks.core_logger_callback)

        self._logger['multi_ranger'] = MultiRangerLogger(self._scf,
                                                         drone_state=self._drone_info,
                                                         callback=self.drone_callbacks.multi_ranger_logger_callback)

        self._logger['motor_thrust'] = MotorThrustLogger(self._scf,
                                                         drone_state=self._drone_info,
                                                         callback=self.drone_callbacks.motor_thrust_logger_callback)

        self._logger['position'] = PositionLogger(self._scf,
                                                  drone_state=self._drone_info,
                                                  callback=self.drone_callbacks.position_logger_callback)

        self._logger['battery'] = BatteryLogger(self._scf,
                                                drone_state=self._drone_info,
                                                callback=self.drone_callbacks.battery_logger_callback)

        # self._logger['loco'] = LocoLogger(self._scf,
        #                                   drone_state=self._drone_info,
        #                                   callback=self.drone_callbacks.loco_logger_callback)

    def _start_logger(self):
        """Start logger
        """
        for logger in self._logger.values():
            logger.start()

    def _stop_logger(self):
        """Stop logger
        """
        for logger in self._logger.values():
            logger.stop() if logger is not None else None

    def perform_power_action(self, action: DronePowerAction):
        """ Set the power action to the drone
        """
        try:
            if self.is_flying:
                LOGGER.debug("Drone is flying. Cannot perform power action")
                return

            if self.is_connect:
                self.disconnect()

            match action:
                case DronePowerAction.POWER_OFF:
                    PowerSwitch(self._uri).platform_power_down()
                case DronePowerAction.REBOOT:
                    PowerSwitch(self._uri).stm_power_cycle()

            LOGGER.debug(
                f'Perform power action {action} on drone {self.uri}')
        except Exception as e:
            LOGGER.error(f"Error when performing power action: {e}")

    def voltage_monitor(self, drone_state: DroneInfo):
        """ This function monitor the voltage of the drone. If the drone is
        below the critical voltage. This will force the drone to land.
        """
        # TODO change to use BatterySetting from dronesetting.py
        # Impossible. Skip
        if drone_state.battery_voltage == 0:
            return
        # Below the shutdown voltage. Disconnect the battery to prevent damage
        # the drone
        if drone_state.battery_voltage < self._voltage_monitor_setting['critical_voltage']:
            LOGGER.warning(
                f"Drone {self._name} ({drone_state.battery_voltage}) is below critical voltage. Disconnecting")
            self.disconnect()

        elif drone_state.battery_voltage < self._voltage_monitor_setting['low_voltage'] and \
                not self._warning.low_voltage:

            # No warning have been given yet
            self._warning.low_voltage = True
            self.is_low_voltage = True
            self.low_voltage_cb.call()
            LOGGER.warning(f'Drone {self.name} is at low voltage!')
            if self.fly_control.is_flying:
                LOGGER.warning(f'Drone {self.name} is landing!')
                self.fly_control.land()
                self.set_arm(False)

    def disconnect(self):
        """Close connection to the Crazyflie. This will block for at least 1 second
        """
        if not self.is_connect:
            LOGGER.warning(str(self) + " is not connected")
            return

        if self.is_flying:
            self.land()

        # Stop all the logger
        self._stop_logger()
        time.sleep(1)
        self._scf.close_link()

        # reset event
        self._drone_decks_event = {
            "z_flow": Event(),
            "loco_position": Event(),
            "multi_ranger": Event()
        }
        LOGGER.drone(str(self) + " disconnected")

    def take_off(self):
        """Crazyflie take off

        Raises:
            DroneException: If connection is not open, or is already flying
        """
        if not self.is_connect:
            raise DroneException("Drone is not connected")
        try:
            self._logger_callbacks.drone_status_callback.call(
                FlyStatus.TAKING_OFF)
            self.fly_control.take_off()
            LOGGER.debug(str(self) + " taking off")

        except Exception as e:
            raise DroneException(str(e))

    def land(self):
        """Crazyflie landing
        """
        if not self.is_connect:
            LOGGER.warning(str(self) + " is not connected")
            return
        elif not self.is_flying:
            LOGGER.warning(str(self) + " is not flying")
            return
        self._logger_callbacks.drone_status_callback.call(FlyStatus.LANDING)
        self.fly_control.land()
        self._logger_callbacks.drone_status_callback.call(FlyStatus.LANDED)
        LOGGER.debug(str(self) + " landing")

    def stream_start(self):
        """ start the video stream
        """
        self._video_stream.start()

    def stream_stop(self):
        """Stop the video stream
        """
        if self._video_stream.is_streaming:
            self._video_stream.stop()

    def _display_connect_msg(self):
        LOGGER.drone(str(self) + " connected")
        LOGGER.debug(f'{self._id} using firmware {self._firmware_version}')

    def set_object_detection(self, value: bool):
        self._video_stream.object_detection_enable = value

    def to_json(self, indent: int | None = None) -> str:
        """to json for jsonpickle. The json string contain the following data of the drone.
        - name
        - address
        - stream address
        - drone state

        Returns:
            str: json representation of drone
        """
        return jsonpickle.encode(
            self.__getstate__(),
            unpicklable=False,
            indent=indent)

    def get_basic_info(self) -> dict:
        """Get basic information of the drone. Including the following information:
        - name
        - address 
        - id
        - stream basic information
        """
        return {
            "name": self.name,
            "uri": self.uri,
            "id": self.id,
            "fly_control": self.fly_control,
            "stream": self._video_stream.get_basic_info(),
        }

    def get_parameter(self, parameter: CFParameter):
        if not self.is_connect:
            raise DroneException("Drone is not connected")

        return self._scf.cf.param.get_value(parameter.value)

    def set_paramter(self, parameter: CFParameter, value):
        if not self.is_connect:
            raise DroneException("Drone is not connected")

        self._scf.cf.param.set_value(parameter.value, value)

    def __getstate__(self) -> dict:
        return {
            'name': self.name,
            'uri': self.uri,
            'id': self.id,
            'fly_control': self.fly_control,
            'stream': self._video_stream,
            'state': self.state
        }

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def name(self) -> str:
        return self._name

    @property
    def stream_url(self) -> str:
        """Drone Live stream address"""
        return self._video_stream.url

    @property
    def stream_ip(self) -> str:
        """Drone Live stream address"""
        return self._video_stream.ip

    @property
    def id(self) -> str:
        """Unique ID for the drone"""
        return self._id

    @property
    def state(self) -> DroneInfo:
        """State of the drone. Base on the log config
        """
        return self._drone_info

    @property
    def is_connect(self) -> bool:
        return self._scf.is_link_open() if self._scf is not None else False

    @property
    def is_flying(self) -> bool:
        return self.fly_control.is_flying

    @property
    def decks(self) -> DroneDecks:
        return self._drone_decks

    @property
    def drone_callbacks(self) -> DroneLoggerCallBacks:
        return self._logger_callbacks

    @property
    def video_callbacks(self) -> StreamCallBacks:
        return self._video_stream.callbacks

    @property
    def object_detection(self) -> bool:
        return self._video_stream.object_detection_enable

    @property
    def object_detection_init(self) -> bool:
        return self._video_stream.model_init

    @property
    def is_arm(self) -> bool:
        value = int(self._scf.cf.param.get_value('system.forceArm'))
        if value == 0:
            return False

        return True

    def __str__(self):
        return f"Drone {self.name}:, id: {self.id} uri: {self.uri}"

    def __repr__(self) -> str:
        return f"Drone {self.name}:, id: {self.id} uri: {self.uri}"


@dataclass(frozen=True)
class FlyControlVelocity:
    """Default velocity setting for different task. m/s for velocity, deg/s for angular velocity
    """

    # type Motion
    # Manually control speed
    manually_control_velocity: VariableCallback = field(
        default_factory=lambda: VariableCallback(Motion(0.2, 0.2, 0.05, 360 / 40)))

    # type Motion
    # max speed for each direction when in auto mode
    auto_velocity: VariableCallback = field(
        default_factory=lambda: VariableCallback(Motion(0.15, 0.15, 0.05, 360 / 20)))

    # type Motion
    # auto avoidance speed
    auto_avoidance_velocity: VariableCallback = field(
        default_factory=lambda: VariableCallback(Motion(0.15, 0.15, 0.1, 0)))

    # type Motion
    hover_correction_velocity: VariableCallback = field(
        default_factory=lambda: VariableCallback(Motion(0.1, 0.1, 0.05, 0)))

    # type Motion
    max_velocity: VariableCallback = field(

        default_factory=lambda: VariableCallback(Motion(0.5, 0.5, 0.1, 360 / 10)))

    # type float
    take_off_velocity: VariableCallback = field(
        default_factory=lambda: VariableCallback(0.15))

    # type float
    land_velocity: VariableCallback = field(
        default_factory=lambda: VariableCallback(0.1))


@dataclass(frozen=True)
class FlyControlDistance:
    """ Default distance setting
    """
    # type Position
    # Margin distance for hover
    hover_correction_min_distance: VariableCallback = field(
        default_factory=lambda: VariableCallback(Position(0.02, 0.02, 0.02)))

    # type Position
    hover_correction_max_distance: VariableCallback = field(
        default_factory=lambda: VariableCallback(Position(0.1, 0.1, 0.05)))

    # type Position
    # Distance for auto avoidance to trigger
    auto_avoidance_trigger_distance: VariableCallback = field(
        default_factory=lambda: VariableCallback(Position(0.25, 0.25, 0.2)))

    # type Position
    # This is the drone dimension. Absolute need to avoid
    auto_avoidance_min_distance: VariableCallback = field(
        default_factory=lambda: VariableCallback(Position(0.15, 0.15, 0.015)))

    # type Position
    # Distance for auto moving to turn. (Should be grater than auto_avoidance_trigger_distance)
    auto_turn_trigger_distance: VariableCallback = field(
        default_factory=lambda: VariableCallback(Position(0.4, 0.4, 0.10)))

    # type float
    auto_slow_distance: VariableCallback = field(
        default_factory=lambda: VariableCallback(0.3))

    # type float
    # Distance for yaw correction
    yaw_trigger_degree: VariableCallback = field(
        default_factory=lambda: VariableCallback(2.5))

    # type float
    yaw_min_correction_degree: VariableCallback = field(
        default_factory=lambda: VariableCallback(1))

    # type float
    moving_side_maintain_distance: VariableCallback = field(
        default_factory=lambda: VariableCallback(0.4))

    # type float
    # The margin distance that allows the drone to drift from the obstacle
    obstacle_maintain_distance_margin: VariableCallback = field(
        default_factory=lambda: VariableCallback(0.1))

    # type float
    take_off_height: VariableCallback = field(
        default_factory=lambda: VariableCallback(0.4))

    landing_cutoff_height: VariableCallback = field(
        default_factory=lambda: VariableCallback(0.1))


@dataclass(frozen=True)
class FlyControlSetting:
    """ Fly control setting

    - fly_mode (FlyMode): NORMAL
    - control_mode (FlyControlMode): AUTO
    - manually_control_hold (bool): False
    - auto_avoid_obstacle (bool): True
    - fly_motion (Motion): Motion(0, 0, 0, 0)
    - hover_position (Position): Position(0, 0, 0)
    - velocity (FlyControlVelocity)
    - distance (FlyControlDistance)
    - avoid_trigger [bool]
    """
    # type FlyMode
    fly_mode: VariableCallback = field(
        default_factory=lambda: VariableCallback(FlyMode.NORMAL))

    # type FlyControlMode
    control_mode: VariableCallback = field(
        default_factory=lambda: VariableCallback(FlyControlMode.AUTO))

    # If user need to holder direction to keep going
    # type bool
    manually_control_hold: VariableCallback = field(
        default_factory=lambda: VariableCallback(False))

    # type bool
    auto_avoid_obstacle: VariableCallback = field(
        default_factory=lambda: VariableCallback(True))

    # type Motion
    hover_position: VariableCallback = field(
        default_factory=lambda: VariableCallback(Position(None, None, None)))

    # type FlyControlVelocity
    velocity: FlyControlVelocity = field(default_factory=FlyControlVelocity)

    # type FlyControlDistance
    distance: FlyControlDistance = field(default_factory=FlyControlDistance)

    avoid_trigger: VariableCallback = field(
        default_factory=lambda: VariableCallback([False, False, False, False]))

    # DEBUG purpose section
    # type Motion
    fly_motion: VariableCallback = field(
        default_factory=lambda: VariableCallback(Motion.zero()))

    # Debug end

    def reset(self):
        """Reset all the setting back to default.

        - fly_mode: NORMAL
        - control_mode: AUTO
        - manually_control_hold: False
        """
        self.fly_mode.set(FlyMode.NORMAL)
        self.control_mode.set(FlyControlMode.AUTO)
        self.manually_control_hold.set(False)
        self.auto_avoid_obstacle.set(True)
        self.fly_motion.set(Motion.zero())

    def __getstate__(self):
        return self.__dict__


class FlyControl:
    def __init__(self, drone: Drone, velocity: float = 0.25, yaw_rate: float = 360 / 5, height=0.4) -> None:
        """Initialize the fly control. Fly control is used to control all the drone movement. 

        Args:
            drone (Drone): Drone is being controlled
            velocity (float, optional): flying velocity. Defaults to 0.25.
            yaw_rate (float, optional): yaw rate . Defaults to 360/5.
            height (float, optional): take off height. Defaults to 0.4.
        """
        self._drone = drone
        self._control_thread = None
        self.setting = FlyControlSetting()
        self.setting.fly_mode.callbacks.add_callback(self._set_fly_mode)
        self._control_mode = FlyControlMode.MANUALLY
        self.fly_status = FlyStatus.LANDED

        self._take_off_height = height
        self._velocity = velocity
        self._yaw_rate = yaw_rate

        self.take_off_cb = Caller()
        self.land_cb = Caller()

        self.land_cb.add_callback(self._land_cb)

    def take_off(self, height: float = None, time_out: float = 5):
        """ take off the drone. If the drone did not reach the target height after `time_out` seconds,
        it will use the current height as the target height. If the current height is lower than 0.1 meter, 
        then it will consider the take off failed.
        """

        if not self._drone.is_connect:
            raise DroneException("Drone is not connected.")

        if self.is_flying:
            raise DroneException("Drone is already flying.")

        try:
            self._is_flying = True
            self._reset_position_estimator()
            if height is None:
                height = self.setting.distance.take_off_height.get()

            current_pos = self._drone.state.position
            self.setting.hover_position.set(Position(
                current_pos.x, current_pos.y, height))

            # TODO REMOVE
            # height = 1
            self.fly_status = FlyStatus.TAKING_OFF

            self._control_thread = FlyControlThread(self._drone)
            self._control_thread.start()

        except Exception as e:
            self.fly_status = FlyStatus.LANDED
            raise e

    def land(self):
        """Land the drone
        """
        if self.is_flying:
            cur_pos = self._drone.state.position
            # Calculate the landing time it will take. Cut off the landing if it takes too long
            landing_timeout = (cur_pos.z - self.setting.distance.landing_cutoff_height.get()
                               ) / self.setting.velocity.land_velocity.get()
            self._control_thread._land_time_out = landing_timeout
            self.setting.hover_position.set(Position(
                cur_pos.x, cur_pos.y, 0))
            self.fly_status = FlyStatus.LANDING

            self._control_thread.join()
            self._control_thread = None

    def _land_cb(self):
        self._is_flying = False
        self.fly_status = FlyStatus.LANDED

    def manually_fly(self, action: FlyCommandManually) -> None:
        """single action control

        Parameters:
            action (FlyControlFlag): action to be performed
        """
        if not self._drone.connect:
            LOGGER.warning(
                f'[Fly Control] {self._drone.name} is not connected')
            return
        if not self.is_flying:
            LOGGER.warning(f'[Fly Control] {self._drone.name} is not flying')
            return

        self._control_thread.add_command(action)

    def go_to(self, position: Position):
        if not self.is_flying:
            LOGGER.debug(f'[Fly Control] {self._drone.name} is not flying')
            return
        if not position or not isinstance(position, Position):
            Logger.warning(
                f'[Fly Control] {self._drone.name} invalid position')
            return
        LOGGER.drone(f'Going to {position}')
        self._control_thread.add_command(position)

    def move_distance(self, distance_x: float, distance_y: float, distance_z: float, velocity: float = None):
        """Move the drone in x, y, z direction for the given distance. (From `motion_commander`). This will block 
        the thread until the drone is in target position. **Avoid using this for long distance when there might
        be obstacle in the way.**

        Args:
            distance_x (float): distance in x direction (m)
            distance_y (float): distance in y direction (m)
            distance_z (float): distance in z direction (m)
            velocity (float, optional): velocity of the movement (m/s). Defaults to velocity for drone.
        """
        if not self.is_ready():
            return

        # distance in 3D
        distance = math.sqrt(distance_x ** 2 + distance_y ** 2 + distance_z ** 2)
        if velocity is None or velocity == 0:
            velocity = self._velocity

        flight_time = distance / velocity

        if distance == 0:
            LOGGER.debug(
                f'[Fly Control] {self._drone.name} distance is 0. Ignore')
            return

        # Recalculate the velocity to match the distance
        velocity_x = velocity * distance_x / distance
        velocity_y = velocity * distance_y / distance
        velocity_z = velocity * distance_z / distance

        self.start_linear_motion(
            Motion(velocity_x, velocity_y, velocity_z, 0))
        time.sleep(flight_time)
        self.stop()

    def stop(self):
        """Send the stop motion to the thread. 
        """
        self.start_linear_motion(Motion.zero())

    def start_linear_motion(self, motion: Motion):
        """Add the given motion in the fly queue.
        """
        if not isinstance(motion, Motion):
            LOGGER.debug(f'[Fly Control] {self._drone.name} invalid motion')
        self._control_thread.add_command(motion)

    def _set_fly_mode(self, mode: FlyMode):
        """Set the fly mode of the drone.
        """
        if self._control_thread is None:
            return
        if mode == FlyMode.HOVER:
            self._control_thread.set_hover(True)
        else:
            self._control_thread.set_hover(False)

    # Debug Operation
    def debug_align_to_axis(self, axis: AxisDirection):
        """Align to the given axis and direction

        Args:
            axis (Axis): Axis needs to align to
        """

        if not self._drone._debug:
            LOGGER.warn(
                f'[Fly Control] {self._drone.name} is not in debug mode')
            return

        if not isinstance(axis, AxisDirection):
            LOGGER.warn(
                f'[Fly control] [debug_align_to_axis] {type(axis)} is not a valid axis')
            return

    def debug_add_command(self, command):
        """Add the given command to the fly queue. This will be executed immediately.
        """
        if not self._drone._debug:
            LOGGER.warn(
                f'[Fly Control] {self._drone.name} is not in debug mode')
            return
        if self._control_thread is not None:
            self._control_thread.add_command(command)

    # Debug end

    def reset(self):
        """Reset fly control. Need to use `set_mc` to set the motion controller before call 
        `take_off`
        """
        self.setting.reset()

    def is_ready(self, display_warning: bool = True):
        """ Determine if the drone is ready to process any fly command. It will check if the drone 
        is already connected and flying. Any of those is false will return false. This will also display
        a debug message to the console. 
        """
        if not self._drone.is_connect:
            if display_warning:
                LOGGER.warning(
                    f'[Fly Control] {self._drone.name} is not connected')
            return False
        if self.fly_status == FlyStatus.LANDED:
            if display_warning:
                LOGGER.warning(
                    f'[Fly Control] {self._drone.name} is not flying')
            return False
        return True

    def _reset_position_estimator(self):
        """Reset the position estimator. This will block for 2.1 seconds
        """
        LOGGER.debug(str(self) + " resetting position estimator")
        self._drone._scf.cf.param.set_value('kalman.resetEstimation', '1')
        time.sleep(0.1)
        self._drone._scf.cf.param.set_value('kalman.resetEstimation', '0')
        time.sleep(2)
        LOGGER.debug(str(self) + " position estimator reset done")

    @property
    def control_mode(self):
        return self.setting.control_mode.get()

    @property
    def fly_mode(self) -> FlyMode:
        return self.setting.fly_mode.get()

    @fly_mode.setter
    def fly_mode(self, value: FlyMode):
        self.setting.fly_mode.set(value)

    @property
    def is_flying(self) -> bool:
        return self.fly_status == FlyStatus.FLYING

    def __getstate__(self):
        return self.setting


class GoToAction(Enum):
    REQUIRE_INIT = auto()
    REQUIRE_AXIS_CHANGE = auto()
    REQUIRE_AXIS_CHANGE_OBSTACLE = auto()  # Obstacle detected
    AXIS_CHANGING = auto()
    MOVING = auto()
    HOLD = auto()


@dataclass
class FlyControlGoToHelper:
    target_position: Position | None = None

    hold_position_x: float | None = None
    hold_position_y: float | None = None
    hold_position_z: float | None = None

    reach_x: bool = False
    reach_y: bool = False
    reach_z: bool = False

    moving_direction: AxisDirection = field(default_factory=AxisDirection)

    action: GoToAction = GoToAction.REQUIRE_INIT
    next_action: GoToAction | None = None

    hold_position: Position | None = None

    # Activate when the drone is moving to avoid obstacle
    avoiding_obstacle: bool = False
    # The direction need to pay attention with. use with `avoiding_obstacle`
    obstacle_direction: Direction = Direction.POSITIVE
    # A line to represent the line of the obstacle. Assume that the obstacle is a straight line, use
    # this to avoid the drone drift to cause turn.
    obstacle_line: Line | None = None

    __yaw_buffer_size = 10

    yaw_buffer = List(__yaw_buffer_size)

    def reset(self):
        self.hold_position_x = None
        self.hold_position_y = None
        self.hold_position_z = None
        self.reach_x = False
        self.reach_y = False
        self.reach_z = False
        self.moving_direction.axis = Axis.Y
        self.action = GoToAction.REQUIRE_INIT
        self.yaw_buffer.clear()
        self.avoiding_obstacle = False


class FlyControlThread(Thread):
    """ Thread for drone control.
    """
    TERMINATE = 'TERMINATE'
    UPDATE_PERIOD = 0.1
    MANUALLY_HOLD_TIME = 1

    def __init__(self, drone: Drone):
        super().__init__()
        self._drone = drone
        self._commander = drone._scf.cf.commander

        self._fly_control = drone.fly_control

        self._drone_state = self._drone.state
        self._control_queue = Queue()
        self._created_time = datetime.now()

        # Credit motion_commander from cflib
        self._z_base = 0.0
        self._z_velocity = 0.0
        self._z_base_time = 0.0

        self.manually_fly_time = 0.0
        self.manually_fly_velocity: Motion = None

        # To remember the position it want to go to
        self._go_to_helper = FlyControlGoToHelper()

        # for auto avoid not interfere with hover
        self.prev_mode = None

        self._current_command = None

        self._path = None

        yaw_control_history_size = 10
        self.yaw_control_history = List(yaw_control_history_size)

        self._maintain_direction: Line | None = None
        self._maintain_yaw: float | None = None

        self.motion = Motion()

        self._dump_flight_data_file = None

        self._land_time_out = 0
        self._land_timer = 0

        if SINGLETON.Config.get_value(ConfigKey.ROOT_DUMP_FLIGHT_DATA):
            self._dump_flight_data_file = get_dump_flight_data_file(
                self._drone.state)
            LOGGER.debug('Dump flight data to ' +
                         self._dump_flight_data_file.name)

    def run(self):
        motion = Motion()
        while True:
            try:
                # For any additional information to be log along with the flight data
                self._extra_log = ''
                motion = Motion()
                # Update every 0.05 seconds
                command = self._get_command()

                if command == self.TERMINATE:
                    break

                # Manually Command
                if isinstance(command, FlyCommandManually):

                    if self.setting.control_mode.get() != FlyControlMode.MANUALLY:
                        LOGGER.debug(
                            f'[Fly Control] {self._drone.name} received manual command but not in manually mode')
                        continue
                    else:
                        self._current_command = command
                        self._fly_control.fly_mode = FlyMode.NORMAL
                # Go to position command
                elif isinstance(command, Position):  # Go to this position
                    self._current_command = command
                    self.setting.fly_mode.set(FlyMode.TARGET)
                    self._go_to_helper.reset()
                    self._go_to_helper.target_position = command

                # Path command
                elif isinstance(command, Path):
                    if not command.is_empty():
                        self._path = command
                        self._current_command = self._path.get_next_position()
                        self.setting.fly_mode.set(FlyMode.TARGET)
                        self._go_to_helper.reset()
                        self._go_to_helper.target_position = self._current_command

                elif isinstance(command, Motion):
                    motion = command

                # Debug option:
                elif isinstance(command, AxisDirection):
                    if not self._drone._debug:
                        LOGGER.warn(
                            f'[Fly Control] {self._drone.name} is not in debug mode')
                    else:
                        self._current_command = command
                        self.set_hover(True)

                if self.fly_status == FlyStatus.TAKING_OFF:
                    self._extra_log = 'Taking Off'
                    current_position = self._drone_state.position
                    if current_position.z < self.setting.distance.take_off_height.get():
                        motion = self.get_hover_velocity(

                            current_position, self.hover_position,
                            override_z=self.setting.velocity.take_off_velocity.get())

                    else:
                        self.fly_status = FlyStatus.FLYING
                        self._fly_control.fly_mode = FlyMode.HOVER
                        self._fly_control.take_off_cb.call()

                elif self.fly_status == FlyStatus.LANDING:
                    self._extra_log = 'Landing'
                    current_position = self._drone_state.position

                    cur_time = time.perf_counter()
                    if current_position.z < self.setting.distance.landing_cutoff_height.get() and \
                            cur_time - self._land_timer >= self._land_time_out:
                        self._send_stop_motor()
                        self.fly_status = FlyStatus.LANDED
                        self._fly_control.land_cb.call()
                        break

                    else:
                        motion = self.get_hover_velocity(
                            current_position, self.hover_position, override_z=self.setting.velocity.land_velocity.get())

                # Process motion
                elif self.fly_status == FlyStatus.FLYING:

                    # Drone might crashed into the obstacle
                    # if int(self._drone_state.thrust) == 0:
                    #     LOGGER.debug("Fly control stopped due to 0 thrust")
                    #     break

                    # Check manually fly time. Only process if the velocity is not 0
                    if self.setting.control_mode.get() == FlyControlMode.MANUALLY and \
                            not self.setting.manually_control_hold.get() and \
                            (isinstance(command,
                                        FlyCommandManually) or self.manually_fly_time != 0):  # Ensure that there is actually some motion need to hold

                        motion = self._process_manually_fly_command(
                            self._current_command)

                        if self.manually_fly_time == 0:
                            # Start flying. Remove all setting for hover
                            self._fly_control.fly_mode = FlyMode.NORMAL
                            self.manually_fly_time = time.perf_counter()

                        else:
                            now = time.perf_counter()

                            if now - self.manually_fly_time > self.MANUALLY_HOLD_TIME:
                                # Manually Finish
                                self.manually_fly_time = 0
                                motion = Motion.zero()
                                # finish flying. Set the mode back to hover
                                self._fly_control.fly_mode = FlyMode.HOVER
                                self._current_command = None
                                self._set_maintain_direction(False)

                    # Debug Purpose Session
                    # All the code below is for debug purpose. It is for testing individual motion to
                    # ensure they all work perfectly

                    # Debug AxisDirection
                    if isinstance(self._current_command, AxisDirection):
                        axis: AxisDirection = self._current_command
                        self._extra_log = f'Debug Rotate Axis'
                        if axis.axis == Axis.X and axis.direction == Direction.POSITIVE:
                            dist = Position(-5, 0, 0)
                        elif axis.axis == Axis.X and axis.direction == Direction.NEGATIVE:
                            dist = Position(5, 0, 0)
                        elif axis.axis == Axis.Y and axis.direction == Direction.NEGATIVE:
                            dist = Position(0, 5, 0)
                        else:
                            dist = Position(0, -5, 0)

                        yaw = self._get_yaw(axis.axis,
                                            dist,
                                            self._drone_state.yaw,
                                            self.setting.distance.yaw_trigger_degree.get(),
                                            self.setting.velocity.auto_velocity.get().yaw)

                        self.yaw_control_history.append(yaw)

                        if self.yaw_control_history.avg() == 0:
                            self._current_command = None

                        motion = motion + Motion(0, 0, 0, yaw)

                    # Debug End

                    # Calculate for go to
                    if self._fly_control.fly_mode == FlyMode.TARGET:
                        motion = self._get_next_movement()

                    # Hover mode
                    if self._fly_control.fly_mode == FlyMode.HOVER:

                        # Ensure no error
                        if self.hover_position is None:
                            self.hover_position = self._drone_state.position
                            LOGGER.debug(
                                '[Fly Control] No hover position. Set to current position to hover point.')

                        # auto hover correction

                        # Calculate the distance between the holding position and the current position

                        motion = self.get_hover_velocity(
                            self._drone_state.position, self.hover_position,
                            motion)

                    if self._maintain_direction is not None:
                        motion = self._direction_correction(motion)

                    # Auto Avoid
                    if self.setting.auto_avoid_obstacle.get():
                        motion = self.auto_avoidance(motion)

                    self._safe_check(motion)

                if not isinstance(motion, Motion):
                    LOGGER.debug(
                        f'[Fly Control] {self._drone.name} invalid motion')
                    motion = Motion.zero()
                    continue
                # Debug / Display purpose

                self.setting.fly_motion.set(motion)
                if SINGLETON.Config.get_value(ConfigKey.ROOT_DUMP_FLIGHT_DATA):
                    self._dump_flight_data(motion)
                self._send_fly_command(motion)

            except Exception as e:
                LOGGER.error(f"[Fly Control Thread] {str(e)}")
                LOGGER.debug(traceback.format_exc())
                break
        if self._dump_flight_data_file is not None:
            self._dump_flight_data_file.close()
        LOGGER.debug(f'[Fly Control Thread] {self._drone.name} terminated')

    def stop(self, no_wait: bool = False):
        """Stop fly control thread. If `no_wait` is True, the thread will clear all the command in the queue
        and stop immediately. 

        Args:
            no_wait (bool, optional): _description_. Defaults to False.
        """
        if no_wait:
            self._control_queue.queue.clear()
        self._control_queue.put(self.TERMINATE)

    def _send_fly_command(self, motion: Motion):
        self._z_base = self._get_z()
        self._z_velocity = motion.vz
        self._z_base_time = time.perf_counter()

        self._drone._scf.cf.commander.send_hover_setpoint(
            motion.vx, motion.vy, motion.yaw, self._get_z())

    def _send_stop_motor(self):
        self._drone._scf.cf.commander.send_stop_setpoint()

    def _get_z(self):
        """Calculate the current z position of the drone
        """
        now = time.perf_counter()
        return self._z_base + self._z_velocity * (now - self._z_base_time)

    def _get_command(self):
        """Return the command from the queue. If queue is empty, return None.
        This will block for `UPDATE_PERIOD` seconds.
        """
        try:
            return self._control_queue.get(timeout=self.UPDATE_PERIOD)
        except Empty:
            return None

    def add_command(self, command: Motion | FlyCommandManually | AxisDirection):
        """Add a new Motion to the queue.

        Args:
            command (FlyCommandFlag): command to be performed
        """
        self._control_queue.put(command)

    def clear_fly_command(self):
        """
        clear all fly command in the queue
        """
        self._control_queue.queue.clear()

    def get_height(self):
        """ Get the current height of the drone
        """
        return self._z_base

    def _process_manually_fly_command(self, flag: FlyCommandManually):
        """Convert the manually fly command to motion
        """
        motion = None
        velocity: Motion = self.setting.velocity.manually_control_velocity.get()
        match flag:
            case FlyCommandManually.FORWARD:
                motion = Motion.forward(velocity.vx)
                if not self.manually_fly_time:
                    self._set_maintain_direction(True)
            case FlyCommandManually.BACKWARD:
                motion = Motion.backward(velocity.vx)
            case FlyCommandManually.LEFT:
                motion = Motion.left(velocity.vy)
            case FlyCommandManually.RIGHT:
                motion = Motion.right(velocity.vy)
            case FlyCommandManually.UP:
                motion = Motion.up(velocity.vz)
            case FlyCommandManually.DOWN:
                motion = Motion.down(velocity.vz)
            case FlyCommandManually.YAW_LEFT:
                motion = Motion.yaw_left(velocity.yaw)
                if not self.hover_set:
                    self.hover_position = self._drone_state.position
            case FlyCommandManually.YAW_RIGHT:
                motion = Motion.yaw_right(velocity.yaw)
                if not self.hover_set:
                    self.hover_position = self._drone_state.position
        yaw = self._drone_state.yaw

        # Convert the local motion to global motion based on the current yaw.
        # -yaw because is from local to global
        # x, y = rotate_axis_coord(motion.vx, motion.vy, -yaw)
        # motion.vx, motion.vy = x, y

        return motion

    def get_hover_velocity(self,
                           drone_position: Position,
                           target: Position,
                           motion: Motion = None,
                           velocity: Motion = None,
                           override_z: float | None = None
                           ) -> Motion:
        """Calculate the require `Motion` to ensure the drone can hover on the target location
        """
        if motion is None:
            motion = Motion()

        max_distance: Position = self.setting.distance.hover_correction_max_distance.get()
        min_distance: Position = self.setting.distance.hover_correction_min_distance.get()

        if velocity is None:
            velocity: Motion = self.setting.velocity.hover_correction_velocity.get()

        if override_z is not None and isinstance(override_z, float):
            velocity.vz = abs(override_z)

        target_x = drone_position.x if target.x == None else target.x
        target_y = drone_position.y if target.y == None else target.y
        target_z = drone_position.z if target.z == None else target.z

        target = Position(target_x, target_y, target_z)

        distance = drone_position - target

        dist_abs = Position.abs(distance)

        correct_velocity = Motion.zero()

        if dist_abs.x > max_distance.x:
            correct_velocity.vx = velocity.vx
        elif dist_abs.x > min_distance.x:
            percentage = percentage_cal(
                dist_abs.x, min_distance.x, max_distance.x)
            correct_velocity.vx = velocity.vx * percentage

        if dist_abs.y > max_distance.y:
            correct_velocity.vy = velocity.vy
        elif dist_abs.y > min_distance.y:
            percentage = percentage_cal(
                dist_abs.y, min_distance.y, max_distance.y)
            correct_velocity.vy = velocity.vy * percentage

        if dist_abs.z > max_distance.z:
            correct_velocity.vz = velocity.vz
        elif dist_abs.z > min_distance.z:
            percentage = percentage_cal(
                dist_abs.z, min_distance.z, max_distance.z)
            correct_velocity.vz = velocity.vz * percentage

        correct_velocity.vy = -correct_velocity.vy if distance.y > 0 else correct_velocity.vy
        correct_velocity.vz = -correct_velocity.vz if distance.z > 0 else correct_velocity.vz
        correct_velocity.vx = -correct_velocity.vx if distance.x > 0 else correct_velocity.vx
        yaw = self._drone_state.yaw
        # if motion.yaw != 0:
        #     yaw -= motion.yaw / 2

        # Convert the global motion to local motion based on the current yaw.
        vx, vy = rotate_axis_coord(
            correct_velocity.vx, correct_velocity.vy, yaw)
        correct_velocity.vx, correct_velocity.vy = vx, vy

        motion = motion + correct_velocity

        return motion

    def _direction_correction(self, motion: Motion) -> Motion:
        """ Maintain the drone are flying to the direction that facing to. This will correct the 
        `y` axis and keep the drone flying to the maintain yaw. 
        """

        if self._maintain_direction is None:
            LOGGER.debug(f'[Fly Control] no direction to maintain')
            return motion

        position = self._drone_state.position
        direction = self._maintain_direction

        yaw = self._drone_state.yaw

        distance = direction.distance(position.to_point2d())

        maintained_min_distance = self.setting.distance.hover_correction_min_distance.get().y
        maintained_max_distance = self.setting.distance.hover_correction_max_distance.get().y

        velocity = self.setting.velocity.hover_correction_velocity.get().vy

        percentage = percentage_cal(
            distance, maintained_min_distance, maintained_max_distance)

        if percentage == 0:
            return motion

        velocity = velocity ** 2 * percentage

        # point on direction
        d_point = Position.from_point2d(direction.points[0])
        l = point_relevant_location_yaw(d_point, position, yaw)

        if l == GDirection.WEST:
            velocity = -velocity
        elif l == GDirection.SAME:
            return motion

        # vx, vy = rotate_axis_coord(0, velocity, yaw)

        # self._get_yaw(self.)

        correction = Motion(0, velocity, 0, 0) + motion
        return correction

    def _get_current_direction(self) -> Line:
        """ Get the current direction of the drone
        """
        position = self._drone_state.position
        # Use current location plus 1 on x axis as the second point. Then rotate it
        target = position + Position(1, 0, 0)

        yaw = self._drone_state.yaw

        p1 = Point(position.x, position.y)
        temp = rotate_axis_coord(target.x, target.y, yaw)
        p2 = Point(temp[0], temp[1])

        return Line(p1, p2)

    def _auto_avoidance_cal(self, dist: float, trigger_dist: float, min_dist: float, velocity: float):
        """Core calculate of the auto avoidance. 
        (abs(distance - trigger) / (trigger - min) )^2
        The closer of the drone the faster the drone will avoid.

        Args:
            distance (float): Distance to the drone
            trigger_dist (float): The distance determine the drone need to avoid
            min_dist: (float): Basically the drone frame
            velocity: (float): The velocity of the drone
        """
        return (abs(dist - trigger_dist) / (trigger_dist - min_dist)) ** 2 * velocity

    def auto_avoidance(self, motion: Motion):
        """
        Determine if the drone needs to avoid the obstacle. The velocity is based 
        on the percentage of the distance need to avoid.
        """

        min_distance: Position = self.setting.distance.auto_avoidance_min_distance.get()
        trigger_distance: Position = self.setting.distance.auto_avoidance_trigger_distance.get()

        avoid_velocity: Motion = self.setting.velocity.auto_avoidance_velocity.get()

        dist_front = self._drone.state.front_distance
        dist_rear = self._drone.state.rear_distance
        dist_left = self._drone.state.left_distance
        dist_right = self._drone.state.right_distance

        # front, rear, left, right
        velocity = [0, 0, 0, 0]

        # Front
        if dist_front < trigger_distance.x:
            dist_front = min_distance.x if dist_front < min_distance.x else dist_front
            velocity[0] = self._auto_avoidance_cal(
                dist_front, trigger_distance.x, min_distance.x, avoid_velocity.vx)

        # Rear
        if dist_rear < trigger_distance.x:
            dist_rear = min_distance.x if dist_rear < min_distance.x else dist_rear
            velocity[1] = self._auto_avoidance_cal(
                dist_rear, trigger_distance.x, min_distance.x, avoid_velocity.vx)

        # Left
        if dist_left < trigger_distance.y:
            dist_left = min_distance.y if dist_left < min_distance.y else dist_left
            velocity[2] = self._auto_avoidance_cal(
                dist_left, trigger_distance.y, min_distance.y, avoid_velocity.vy)

        # Right
        if dist_right < trigger_distance.y:
            dist_right = min_distance.y if dist_right < min_distance.y else dist_right
            velocity[3] = self._auto_avoidance_cal(
                dist_right, trigger_distance.y, min_distance.y, avoid_velocity.vy)

        if velocity[0] != 0 and velocity[1] != 0:
            motion.vx = 0  # Too close both side of the drone. Stop all the movement on x axis
        elif velocity[0] != 0:
            motion.vx = -velocity[0]
        elif velocity[1] != 0:
            motion.vx = velocity[1]

        if velocity[2] != 0 and velocity[3] != 0:
            motion.vy = 0
        elif velocity[2] != 0:
            motion.vy = -velocity[2]
        elif velocity[3] != 0:
            motion.vy = velocity[3]

        for count, v in enumerate(velocity):
            # update the trigger status
            self.setting.avoid_trigger.get()[count] = v != 0

        # avoidance trigger
        if velocity.count(0) != 4:
            if self._fly_control.fly_mode == FlyMode.HOVER:
                self._fly_control.fly_mode = FlyMode.NORMAL
                self.prev_mode = FlyMode.HOVER
        else:
            if self.prev_mode == FlyMode.HOVER:
                self.prev_mode = None
                self._fly_control.fly_mode = FlyMode.HOVER
        return motion

    def set_hover(self, value: bool):
        """Set all the required parameters for `enable` disable `hover`"""
        # Enable Hover
        if value:
            self.hover_position = self._drone_state.position

        else:
            # When disable hover, also clear the hover velocity
            self.hover_position = Position(None, None, None)
            self.add_command(Motion.zero())

    def is_drone_thrust_normal(self) -> bool:
        """Determine whether the drone is in the normal thrust state. If any of the thrust is 0,
        the drone is not in the normal state.
        """
        return self._drone_state.thrust > 0 and \
               self._drone_state.thrust_m1 > 0 and \
               self._drone_state.thrust_m2 > 0 and \
               self._drone_state.thrust_m3 > 0 and \
               self._drone_state.thrust_m4 > 0

    def _reach_target(self, target: Position, margin: Position) -> bool:
        """Determine if the drone reach the target. If the drone reach the margin of the target,
        return true. The margin of the target is define in the setting.
        Example:
        >>> _reach_target(Position(0,0.1,0), ) # Margin: 0.1,0.1,0.05, current: 0,0.05,0
        True
        """
        return self._drone_state.position.with_in_range(target, margin, ignore_z=True)

    def _get_next_movement(self) -> Motion:
        """Calculate the next drone location based on the current location and the current
        velocity.

        Returns:
            Position: next drone location
        """
        # TODO Situation when the target position is near the obstacle. List it is at the distance less than
        # avoid distance. 
        current_pos = self._drone_state.position
        target = self._go_to_helper.target_position

        velocity: Motion = self.setting.velocity.auto_velocity.get()

        dist_to_target: Position = current_pos - target

        dist_to_target_abs = Position.abs(dist_to_target)

        current_yaw = self._drone_state.yaw

        yaw_margin: float = self.setting.distance.yaw_trigger_degree.get()
        max_yaw: float = velocity.yaw

        turn_trigger_distance: Position = self.setting.distance.auto_turn_trigger_distance.get()

        hover_trigger_range: Position = self.setting.distance.hover_correction_max_distance.get()
        hover_min_range: Position = self.setting.distance.hover_correction_min_distance.get()
        motion = Motion.zero()

        if self._reach_target(target, hover_min_range):

            # Check if currently is in path mode
            if self._path is not None:
                next_position = self._path.get_next_position()
                if next_position is not None:
                    self._go_to_helper.reset()
                    self._go_to_helper.target_position = next_position

                # path is empty now. Clear it
                self._path = None
            self.setting.fly_mode.set(FlyMode.HOVER)
            self._go_to_helper.reset()
            return motion

        # Correct yaw if not facing the direction

        # TODO adjust the z position

        # Check Actions
        # Need to rotate to the target direction. always rotate to Y axis first

        if self._go_to_helper.action == GoToAction.REQUIRE_INIT or \
                self._go_to_helper.action == GoToAction.REQUIRE_AXIS_CHANGE \
                or self._go_to_helper.action == GoToAction.REQUIRE_AXIS_CHANGE_OBSTACLE:

            if self._go_to_helper.action == GoToAction.REQUIRE_INIT:
                self._go_to_helper.reset()
                # check if the which axis need to rotate first. Prefer to rotate to Y axis fist
                if dist_to_target_abs.y > turn_trigger_distance.y:
                    self._go_to_helper.moving_direction.axis = Axis.Y
                else:
                    self._go_to_helper.moving_direction.axis = Axis.X
            elif self._go_to_helper.action == GoToAction.REQUIRE_AXIS_CHANGE_OBSTACLE:

                # Distance to left and right (left, right)
                dist = (self._drone_state.left_distance,
                        self._drone_state.right_distance)
                dist = (round_up(dist[0], 0.05), round_up(dist[1], 0.05))
                # the more distance the more likely can be move around the obstacle
                if dist[1] >= dist[0]:
                    self._go_to_helper.moving_direction = self._go_to_helper.moving_direction.rotate_right()
                    self._go_to_helper.obstacle_direction = Direction.POSITIVE
                else:
                    self._go_to_helper.moving_direction = self._go_to_helper.moving_direction.rotate_left()
                    self._go_to_helper.obstacle_direction = Direction.NEGATIVE
                self._go_to_helper.avoiding_obstacle = True

            else:  # Require Axis Change
                self._go_to_helper.moving_direction.axis = Axis.Y if self._go_to_helper.moving_direction.axis == Axis.X else Axis.X

            self.go_to_set_axis_changing()

        if self._go_to_helper.action == GoToAction.HOLD:
            # Hold the position until it is in the acceptable range. then do the next action
            if self._reach_target(self._go_to_helper.hold_position, hover_trigger_range):
                self._go_to_helper.action = self._go_to_helper.next_action
                self._go_to_helper.next_action = None
                LOGGER.debug(
                    f'Hold position reached, next action: {self._go_to_helper.action}')
            else:
                correction = self.get_hover_velocity(
                    self._drone_state.position, self._go_to_helper.hold_position)
                motion = motion + correction
                self._extra_log = f'Hold position: {self._go_to_helper.hold_position}, correction: {correction}'

        if self._go_to_helper.action == GoToAction.AXIS_CHANGING:
            self._extra_log = (
                f"Axis Changing to {self._go_to_helper.moving_direction.axis}")

            motion = self.get_hover_velocity(self._drone_state.position,
                                             self.hover_position)

            yaw = self._get_yaw(axis=self._go_to_helper.moving_direction.axis,
                                dist=dist_to_target,
                                current_yaw=current_yaw,
                                margin=yaw_margin,
                                max_yaw=max_yaw)

            self._go_to_helper.yaw_buffer.append(yaw)

            motion.yaw = yaw

            # Ensure the average of yaw
            if self._go_to_helper.yaw_buffer.avg() == 0:
                self._change_to_hold(self.hover_position, GoToAction.MOVING)
                self._go_to_helper.moving_direction = AxisDirection.from_yaw(
                    current_yaw)
                self._set_maintain_direction(True)
                self.hover_position = Position(None, None, None)
                # self._go_to_helper.hold_position = self._drone_state.position

        elif self._go_to_helper.action == GoToAction.MOVING:
            # Obstacle detected need to change direction
            if self._drone_state.front_distance < turn_trigger_distance.x:
                self._go_to_helper.action = GoToAction.REQUIRE_AXIS_CHANGE_OBSTACLE
                return motion
            slow_dist: float = self.setting.distance.auto_slow_distance.get()
            if not self._go_to_helper.avoiding_obstacle:  # Normal move
                # Moving alone the X axis
                if self._go_to_helper.moving_direction.axis == Axis.X:

                    thrust_percent = percentage_cal(
                        -dist_to_target.x,
                        max_value=slow_dist,
                        min_value=0)
                    self._extra_log = f" To X. Thrust Percent: {thrust_percent}, dist_to_target.x: {dist_to_target.x}"

                # Moving alone with Y axis
                else:
                    thrust_percent = percentage_cal(
                        -dist_to_target.y,
                        max_value=slow_dist,
                        min_value=0)

                if thrust_percent == 0 or self._is_pass_target(
                        self._go_to_helper.moving_direction, self._drone_state.position,
                        self._go_to_helper.target_position):
                    # starting approaching the target. Use the hold mode
                    hover_pos = get_projection_point(self._maintain_direction, self._drone_state.position)
                    self._change_to_hold(hover_pos,
                                         GoToAction.REQUIRE_AXIS_CHANGE)

                else:
                    thrust_percent = thrust_percent * 2
                    vx = velocity.vy * thrust_percent
                    motion.vx = vx
            else:  # avoiding the obstacle
                monitor_dist = self._drone_state.left_distance if self._go_to_helper.obstacle_direction == Direction.NEGATIVE \
                    else self._drone_state.right_distance

                # dist_to_wall = self._go_to_helper.obstacle_line.distance(current_pos.to_point2d())
                # if dist_to_wall > self.setting.distance.obstacle_maintain_distance_margin.get() + self.setting.distance.moving_side_maintain_distance.get():
                if monitor_dist > self.setting.distance.moving_side_maintain_distance.get() + \
                        self.setting.distance.obstacle_maintain_distance_margin.get():
                    if self._go_to_helper.obstacle_direction == Direction.NEGATIVE:
                        self._go_to_helper.moving_direction = self._go_to_helper.moving_direction.rotate_right()
                    else:
                        self._go_to_helper.moving_direction = self._go_to_helper.moving_direction.rotate_left()
                    self._go_to_helper.avoiding_obstacle = False
                    self.go_to_set_axis_changing()
                else:
                    motion = Motion.forward(self.setting.velocity.auto_velocity.get().vx)

        return motion

    def _change_to_hold(self, hold_position: Position, next_action: GoToAction):
        self._go_to_helper.action = GoToAction.HOLD
        self._go_to_helper.hold_position = hold_position
        self._go_to_helper.next_action = next_action

    def _set_maintain_direction(self, enable: bool):
        if enable:
            self._maintain_direction = self._get_current_direction()
            self._maintain_yaw = self._drone_state.yaw
        else:
            self._maintain_direction = None
            self._maintain_yaw = None

    def _is_pass_target(self, direction: AxisDirection, pos: Position, target: Position) -> bool:
        """ Check if the drone is pass the target position
        """
        gdirection = point_relevant_location(target, pos)

        if direction == AxisDirection.x_positive():
            if gdirection[0] == GDirection.NORTH:
                return True
            return False
        elif direction == AxisDirection.x_negative():
            if gdirection[0] == GDirection.SOUTH:
                return True
            return False
        elif direction == AxisDirection.y_positive():
            if gdirection[1] == GDirection.WEST:
                return True
            return False
        elif direction == AxisDirection.y_negative():
            if gdirection[1] == GDirection.EAST:
                return True
            return False
        # Unknown direction Always assume it is pass the target
        return True

    def _get_yaw(self, axis: Axis,
                 dist: Position,
                 current_yaw: float,
                 margin: float,
                 max_yaw: float = None,
                 direction: Direction = None
                 ) -> float:
        """Get the needed yaw to the face the direction for the axis. if the require yaw is 
        larger to the max yaw, then the max yaw will be used instead.

        ```
                0
                ^
                |
        +90 <---|---> -90
                |
                v
               180
        ```

        - `+` yaw: turn right
        - `-` yaw: turn left

        Args:
            axis (Axis): Axis to face
            dist (Position): Distance to the target
            current_yaw (float): current yaw
            margin (float): margin for the yaw
            max_yaw (float, optional): max yaw can turn. Defaults to None.
        """
        # !TODO: When the drone is at opposite side of the target. There might be an issue
        yaw = 0

        target_yaw = 0

        if direction is None:
            if axis == Axis.X:
                if dist.x < 0:
                    direction = Direction.POSITIVE
                else:
                    direction = Direction.NEGATIVE

            else:
                if dist.y < 0:
                    direction = Direction.NEGATIVE
                else:
                    direction = Direction.POSITIVE

        target = AxisDirection(axis, direction)
        target_yaw = get_yaw_from_axis_direction(target)

        if target_yaw == 0:
            move_yaw = current_yaw - target_yaw
            # Only turn if the yaw is not within the margin
            if abs(move_yaw) > margin:
                # On the left of the target. Turn right
                if move_yaw > 0:
                    yaw = min(max_yaw, move_yaw)
                    # max_yaw if move_yaw > max_yaw else move_yaw
                else:
                    # On the right of the target. Turn left
                    yaw = max(-max_yaw, move_yaw)
        elif target_yaw == 180:
            move_yaw = abs(abs(current_yaw) - target_yaw)
            if move_yaw > margin:
                if current_yaw > 0:
                    # turn left
                    yaw = -min(max_yaw, move_yaw)
                else:
                    # turn right
                    yaw = min(max_yaw, move_yaw)
        elif target_yaw == 90:
            move_yaw = abs(current_yaw) - target_yaw
            if current_yaw < 0 and current_yaw > -90:
                move_yaw += 2 * current_yaw
            elif current_yaw < -90:
                move_yaw += 2 * (180 - abs(current_yaw))

            if abs(move_yaw) > margin:
                if abs(current_yaw) < 90:
                    yaw = max(-max_yaw, move_yaw)
                else:
                    yaw = min(max_yaw, move_yaw)

        elif target_yaw == -90:
            move_yaw = abs(abs(current_yaw) - abs(target_yaw))
            if current_yaw > 0 and current_yaw < 90:
                move_yaw += 2 * current_yaw
            elif current_yaw > 90:
                move_yaw += 2 * (180 - abs(current_yaw))

            if abs(move_yaw) > margin:
                if abs(current_yaw) < 90:
                    yaw = min(max_yaw, move_yaw)
                else:
                    yaw = max(-max_yaw, -move_yaw)

        return yaw

    def _get_yaw_new(self, maintain_yaw: float, current_yaw: float, margin: float, max_yaw: float):
        # TODO maintain at any yaw
        pass

    def _safe_check(self, motion: Motion):
        """ This function ensure that the maximum velocity and acceleration is not exceeded.
        """

        max_velocity: Motion = self.setting.velocity.max_velocity.get()

        if abs(motion.vx) > max_velocity.vx:
            LOGGER.debug(f'vx {motion.vx} exceed max velocity.')
            motion.vx = max_velocity.vx if motion.vx > 0 else -max_velocity.vx

        if abs(motion.vy) > max_velocity.vy:
            motion.vy = max_velocity.vy if motion.vy > 0 else -max_velocity.vy

        if abs(motion.vz) > max_velocity.vz:
            motion.vz = max_velocity.vz if motion.vz > 0 else -max_velocity.vz

    def set_height(self, height: float):
        self._z_base = height

    def _dump_flight_data(self, motion: Motion):
        if not self._dump_flight_data_file:
            return
        cur_time = time.strftime("%H:%M:%S")
        state_data = self._drone_state.to_csv()
        data = f'{cur_time},{state_data},{motion.to_csv()},{self.setting.hover_position.get().to_csv()},{self.setting.fly_mode.get()},"{self._current_command}","{self._extra_log}"'
        print(data, file=self._dump_flight_data_file)

    def set_land_timeout(self, timeout: float):
        self._land_time_out = timeout
        self._land_timer = time.perf_counter()

    def go_to_set_axis_changing(self):
        self._go_to_helper.action = GoToAction.AXIS_CHANGING
        self._go_to_helper.yaw_buffer.clear()
        self._set_maintain_direction(False)
        self.hover_position = self._drone_state.position

    @property
    def setting(self) -> FlyControlSetting:
        return self._fly_control.setting

    @property
    def velocity(self) -> FlyControlVelocity:
        return self._fly_control.setting.velocity

    @property
    def hover_position(self) -> Position:
        return self._fly_control.setting.hover_position.get()

    @hover_position.setter
    def hover_position(self, value: Position):
        self._fly_control.setting.hover_position.set(value)

    @property
    def fly_status(self) -> FlyStatus:
        return self._fly_control.fly_status

    @fly_status.setter
    def fly_status(self, value: FlyStatus):
        self._fly_control.fly_status = value

    @property
    def hover_set(self) -> bool:
        return self.hover_position.x is not None and self.hover_position.y is not None and self.hover_position.z is not None

    def __repr__(self) -> str:
        created_time = self._created_time.strftime("%Y-%m-%d %H:%M:%S")
        return super().__repr__() + f"({self._drone.name}, {created_time} )"
