import jsonpickle
from config.config import Config
from .drone import Drone
from log.logger import LOGGER

from cflib.crtp import init_drivers
from cflib.drivers.crazyradio import Crazyradio

from threading import Thread


class Hub:
    def __init__(self, config: Config):
        init_drivers()
        self._drones = self.create_drone_from_config(config)

    def create_drone_from_config(self, config: Config):
        """Create a drone from the config file
        """
        drones = {}
        drone_config = config.get_drones()
        for _, drone in drone_config.items():
            drones[drone['name']] = Drone(drone['name'],
                                          drone['uri'],
                                          stream_url=drone['stream'],
                                          debug=config.get_value('debug'),
                                          )
        return drones

    def disconnectAll(self):
        """Disconnect everything and exit
        """
        threads = []
        for drone in self._drones.values():
            if drone.is_connect:
                thread = Thread(target=drone.disconnect)
                threads.append(thread)
                thread.start()

                # TODO Remove in the future
                thread = Thread(target=drone.stream_stop)
                threads.append(thread)
                thread.start()

        for thread in threads:
            thread.join()

    def to_json(self, indent: int | None = None) -> str:
        """to json for jsonpickle

        Args:
            indent (int | None, optional): _description_. Defaults to None.

        Returns:
            str: _description_
        """
        return jsonpickle.encode(self._drones, unpicklable=False, indent=indent)

    def get_basic_info(self) -> dict:
        """Get only the basic information of the drones. Each drone contain the following 
        basic information. 
        """
        d = {}
        for name, drone in self._drones.items():
            d[name] = drone.get_basic_info()
        return d

    def low_battery_notify(self, ip: str):
        """This function is called when a onboard camera is on low battery. 
        Args:
            ip (str): ip address of the onboard camera
        """
        drone = None
        for d in self._drones.values():  # type: Drone
            if d.stream_ip == ip:
                drone = d
                break

        if drone is None:
            LOGGER.info(f'Low battery signal received, but no drone found for ip {ip}')
            return

        drone.onboard_low_voltage_cb.call()
        LOGGER.debug(f'Low battery notification for {drone.name}@{ip}')


    def __getstate__(self) -> dict:
        """Get state for pickle
        """
        return self._drones

    @property
    def drones(self) -> dict:
        return self._drones
