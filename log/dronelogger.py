from typing import Callable

from . import LogVariable, DroneInfo

from cflib.crazyflie.log import LogConfig
from cflib.crazyflie import syncCrazyflie
from cflib.utils.callbacks import Caller

import logging

class DroneLogger:
    """
    A wrapper class for cflib.crazyflie.log.LogConfig. It include some of the logging 
    parameters and the type of the variables. It is asynchronously updated.
    """

    def __init__(self,
                 scf: syncCrazyflie,
                 variables: list[LogVariable],
                 drone_state: DroneInfo = None,
                 name: str = "custom log",
                 display_log: bool = False,
                 callback: Caller = None,
                 period_in_ms: int = 100
                 ) -> None:
        """Constructor

        Args:
            scf (syncCrazyflie): the syncCrazyflie object
            variables (list[LogVariable]): list of LogVariable to add
            drone_state (DroneState, optional): the drone state. Defaults to None.
            name (str, optional): name of the log. Defaults to "custom log".
            display_log (bool, optional): display the log. Defaults to True.
            callback (Caller, optional): callback to update the UI, must take a single 
                parameter as `DroneState`. Defaults to None.
            period_in_ms (int, optional): period between update. Min 10ms Defaults to 100.
        """
        self._logger = LogConfig(
            name, 10 if period_in_ms < 10 else period_in_ms)
        self._logging = logging.getLogger(self.__class__.__name__)
        self._add_variables(variables)
        scf.cf.log.add_config(self._logger)
        self._logger.data_received_cb.add_callback(self.log_callback)
        self._display_log = display_log
        # Internal Drone State
        self._drone_state = DroneInfo()
        # Drone State pass from the outside. Should belong to the `Drone`
        self._drone_drone_state = drone_state
        self._callback = callback

    def _add_variables(self, variables: list[LogVariable]) -> None:
        """add variables to the log

        Args:
            variables (list[LogVariable]): list of LogVariable to add
        """
        if not isinstance(variables, list):
            self._logging.error('Add variable failed, variables is not a list')
            raise TypeError('Add variable failed, variables is not a list')
        for var in variables:
            # Get the value of the enum
            value = var.value
            self._logger.add_variable(value[0], value[1].value)

    def log_callback(self, timestamp: str, data: dict, logconf: dict) -> None:
        """log call back function to print the data, timestamp is the time 
        since the drone switch on
        """
        self._drone_state.update(data)
        if self._callback is not None:
            self._callback.call(self._drone_state)
        if self._drone_drone_state is not None:
            self._drone_drone_state.update(self._drone_state.state)
        if (self._display_log):
            self._logging.debug(f"[{timestamp}] [{logconf.name}] {data}")

    def start(self):
        self._logger.start()

    def stop(self):
        self._logger.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class CoreLogger(DroneLogger):
    """Core logger contain Battery, Pitch, Roll and Yaw
    """
    _LOG_VARIABLES = [
        LogVariable.CORE_PITCH,
        LogVariable.CORE_ROLL,
        LogVariable.CORE_YAW,
    ]

    def __init__(self,
                 scf: syncCrazyflie,
                 drone_state: DroneInfo = None,
                 display_log: bool = False,
                 callback: Caller = None,
                 period_in_ms: int = 10
                 ) -> None:
        super().__init__(scf,
                         self._LOG_VARIABLES,
                         drone_state,
                         "Core",
                         display_log,
                         callback,
                         period_in_ms)
        
class BatteryLogger(DroneLogger):
    """Battery logger contain Battery info. 1.5s update rate
    """
    _LOG_VARIABLES = [
        LogVariable.POWER_MANAGER_BATTERY_LEVEL,
        LogVariable.POWER_MANAGER_BATTERY_VOLTAGE,
        LogVariable.POWER_MANAGER_BATTERY_STATE
    ]

    def __init__(self,
                 scf: syncCrazyflie,
                 drone_state: DroneInfo = None,
                 display_log: bool = False,
                 callback: Caller = None,
                 period_in_ms: int = 100
                 ) -> None:
        super().__init__(scf,
                         self._LOG_VARIABLES,
                         drone_state,
                         "Battery",
                         display_log,
                         callback,
                         period_in_ms)
        
        
class MotorThrustLogger(DroneLogger):
    """Motor thrust logger contain Motor thrust info. Including all motor and 
    over thrust. 0.25s interval
    """
    _LOG_VARIABLES = [
        LogVariable.CORE_THRUST,
        LogVariable.MOTOR_M1,
        LogVariable.MOTOR_M2,
        LogVariable.MOTOR_M3,
        LogVariable.MOTOR_M4,
    ]
    def __init__(self,
                 scf: syncCrazyflie,
                 drone_state: DroneInfo = None,
                 display_log: bool = False,
                 callback: Caller = None,
                 period_in_ms: int = 250
                 ) -> None:
        super().__init__(scf,
                         self._LOG_VARIABLES,
                         drone_state,
                         "Motor Thrust",
                         display_log,
                         callback,
                         period_in_ms)
        
class MultiRangerLogger(DroneLogger):
    """Multi Ranger logger contain Multi Ranger info. 20ms interval
    """
    _LOG_VARIABLES = [
    LogVariable.MULTI_RANGER_FRONT,
    LogVariable.MULTI_RANGER_LEFT,
    LogVariable.MULTI_RANGER_RIGHT,
    LogVariable.MULTI_RANGER_REAR,
    LogVariable.MULTI_RANGER_DOWN,
    ]
    def __init__(self,
                 scf: syncCrazyflie,
                 drone_state: DroneInfo = None,
                 display_log: bool = False,
                 callback: Caller = None,
                 period_in_ms: int = 10
                 ) -> None:
        super().__init__(scf,
                         self._LOG_VARIABLES,
                         drone_state,
                         "Multi Ranger",
                         display_log,
                         callback,
                         period_in_ms)
        
class PositionLogger(DroneLogger):
    """Position logger contain location information. 20ms interval
    """
    _LOG_VARIABLES = [
        LogVariable.POSITION_X,
        LogVariable.POSITION_Y,
        LogVariable.POSITION_Z,
    ]
    def __init__(self,
                 scf: syncCrazyflie,
                 drone_state: DroneInfo = None,
                 display_log: bool = False,
                 callback: Caller = None,
                 period_in_ms: int = 10
                 ) -> None:
        super().__init__(scf,
                         self._LOG_VARIABLES,
                         drone_state,
                         "Position",
                         display_log,
                         callback,
                         period_in_ms)
        
class LocoLogger(DroneLogger):
    """Loco logger contain loco info. 1s interval
    """
    _LOG_VARIABLES = [
        LogVariable.LOCO_MODE
    ]
    def __init__(self,
                 scf: syncCrazyflie,
                 drone_state: DroneInfo = None,
                 display_log: bool = False,
                 callback: Caller = None,
                 period_in_ms: int = 100
                 ) -> None:
        super().__init__(scf,
                         self._LOG_VARIABLES,
                         drone_state,
                         "Loco",
                         display_log,
                         callback,
                         period_in_ms)
                         