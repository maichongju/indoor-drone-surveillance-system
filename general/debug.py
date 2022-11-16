import os
import time

from log import DroneInfo


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

    header = f'time,{state.to_csv_header()},motion.vx,motion.vy,motion.vz,motion.yaw,hover.x,hover.y,hover.z,mode,command,extra'

    print(header, file=file)
    return file
