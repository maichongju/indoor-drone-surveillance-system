import os
import time

from log import DroneInfo
from general.enum import Enum


def get_dump_flight_data_file(state: DroneInfo, uri: str, prefix: str = None, folder: str = 'logs/flight_data/'):
    """Return a `File` object for the dump flight data file. Named
    with the `prefix` + `current time`. The file object already contain the 
    first header row.
    """
    if not os.path.exists(folder):
        os.makedirs(folder)
    file_name = f'{time.strftime("%Y-%m-%d_%H-%M-%S")}_{uri[-2:]}.csv'
    if prefix is not None:
        file_name = prefix + '_' + file_name

    file = open(folder + file_name, 'w')

    extra_log = DroneExtraLog.to_csv_header()

    header = f'time,{state.to_csv_header()},' \
             f'motion.vx,motion.vy,motion.vz,motion.yaw,hover.x,hover.y,hover.z,mode,command,' \
             f'{extra_log}'

    print(header, file=file)
    return file


# class DroneExtraLog(str, Enum):
#     MODE = 'mode'
#     HOLD_POS = 'hold_pos'
#     HOLD_CORRECTION = 'hold_correction'
#     CORRECTION = 'correction'
#     AXIS_CHANGE_TO = 'axis_change_to'
#     CURRENT_AXIS = 'current_axis'
#     DISTANCE_TO_TARGET = 'distance_to_target'
#     THRUST_PERCENT = 'thrust_percent'
#     MAINTAIN_DIRECTION_OFFSET = 'maintain_direction_offset'
#     GO_TO_MODE = 'go_to_mode'
#     AVOIDING_OBSTACLE = 'avoiding_obstacle'
#     OBSTACLE_DIRECTION = 'obstacle_direction'
#     OBSTACLE_DISTANCE_AVG = 'obstacle_distance_avg'

class DroneExtraLog(str, Enum):
    STATUS = 'status'
    HOLD_POS = 'hold_pos'
    HOLD_CORRECTION = 'hold_correction'
    CORRECTION = 'correction'
    AXIS_CHANGE_TO = 'axis_change_to'
    CURRENT_AXIS = 'current_axis'
    DISTANCE_TO_TARGET = 'distance_to_target'
    THRUST_PERCENT = 'thrust_percent'
    MAINTAIN_DIRECTION_OFFSET = 'maintain_direction_offset'
    GO_TO_MODE = 'go_to_mode'
    AVOIDING_OBSTACLE = 'avoiding_obstacle'
    OBSTACLE_DIRECTION = 'obstacle_direction'
    OBSTACLE_DISTANCE_AVG = 'obstacle_distance_avg'

    @staticmethod
    def to_csv_header():
        """
        return a string with all the header for the DroneExtraLog
        """
        return ','.join([str(log.value) for log in DroneExtraLog])

    @staticmethod
    def convert_dict_to_csv(data: dict):
        """
        Convert a dict to a csv string
        Args:
            data: dict to convert

        Returns:
            csv string
        """

        return ','.join([f'{data.get(log.value)}' for log in DroneExtraLog])