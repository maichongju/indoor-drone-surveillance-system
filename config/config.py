from __future__ import annotations
from copy import deepcopy
from http import server
import json
from typing import Any
import tomli
import logging

from enum import Enum
from dataclasses import astuple, dataclass


LOGGER_LEVEL_DRONE = logging.INFO + 5

WARNING = logging.WARNING
ERROR = logging.ERROR


class ConfigError(Exception):
    pass


class ErrorMessage(Enum):
    INVALID_FILE = "Invalid config value"
    INVALID_VALUE = "Invalid value for %s"
    INVALID_VALUE_CUSTOM = "Invalid value for %s. %s"


class ConfigCategory(Enum):
    DRONE = "drone"
    LOGGING = "logging"
    GUI = "gui"
    SERVER = "server"
    ROOT = ""
    
    @property
    def name(self):
        return self.value


class ConfigKey(Enum):
    """Config key enum. 
    
    value (category, key) : category and config key
    category (str) : category name
    category_raw (ConfigCategory) : category enum
    key (str) : key name
    """
    DRONE_NAME = ConfigCategory.DRONE, "name", str
    DRONE_URI = ConfigCategory.DRONE, "uri", str
    DRONE_STREAM = ConfigCategory.DRONE, "stream" ,str
    DRONE_ENABLE = ConfigCategory.DRONE, "enable", bool

    LOGGING_ENABLE = ConfigCategory.LOGGING, "enable", bool
    LOGGING_LEVEL = ConfigCategory.LOGGING, "level", str
    LOGGING_LOG_FILE = ConfigCategory.LOGGING, "log_file", str

    GUI_DEBUG = ConfigCategory.GUI, "debug", bool
    GUI_SHOW_ON_START = ConfigCategory.GUI, "show_on_start", bool

    SERVER_ENABLE = ConfigCategory.SERVER, "enable", bool
    SERVER_PORT = ConfigCategory.SERVER, "port", int
    SERVER_HOST = ConfigCategory.SERVER, "host", str
    SERVER_DEBUG = ConfigCategory.SERVER, "debug", bool
    SERVER_LOG_FILE = ConfigCategory.SERVER, "log_file", str
    
    ROOT_DEBUG = ConfigCategory.ROOT, "debug", bool
    ROOT_DUMP_FLIGHT_DATA = ConfigCategory.ROOT, "dump_flight_data", bool

    @property
    def category_raw(self):
        return self.value[0]
    
    @property
    def category(self):
        return self.value[0].value
    
    @property
    def key(self):
        return self.value[1]
    
    @property
    def type(self):
        return self.value[2]
    
    def __str__(self):
        return f'{self.category}.{self.key}'


@dataclass
class ConfigErrorMessage:
    level: int
    msg: str

    def __iter__(self):
        return iter(astuple(self))


DEFAULT_CONFIG = {
    'debug': False,
    'dump_flight_data': False,
    'drone': {},
    'logging': {
        'enable': False,
        'level': logging.INFO,
        'log_file': 'logs/client.log'
    },
    'gui': {
        "debug": False,
        "show_on_start": False
    },
    'server': {
        'enable': True,
        'host': 'localhost',
        'port': 8080,
        'log_file': 'logs/flask.log',
        'debug': False
    }
}


class Config:
    """Config class for generating and validation from config file
    """

    def __init__(self, config_file: str = "config.toml") -> None:
        self.config_file = config_file
        self._error_msg = []
        source = self._get_config()
        self._config_validation(source)

    def display_error_messages(self) -> None:
        """
        During config, the logger has not been set up properly. Therefor messages are not
        displayed. This function should call after logger is set up by calling logging_init().
        """
        if len(self._error_msg) == 0:
            return

        for level, msg in self._error_msg:
            match level:
                case logging.ERROR:
                    logging.error(msg)
                case logging.WARNING:
                    logging.warning(msg)
                case logging.DEBUG:
                    logging.debug(msg)

    def get_value(self, key: ConfigKey | ConfigCategory):
        """ Get the config value for the key. If key does not exist, 
        None will return 
        Examples:
        
        # TODO: Add Example
        """
        if isinstance(key, ConfigCategory):
            if key == ConfigCategory.ROOT:
                raise ValueError("Can not get the entire root. Use ConfigKey instead")
            return self._config.get(key.value, None)
        elif isinstance(key, ConfigKey):
            if key.category_raw == ConfigCategory.DRONE:
                raise ValueError("ConfigKey.DRONE is not supported. Use get_drones() instead")
            elif key.category_raw == ConfigCategory.ROOT:
                return self._config.get(key.key, None)
            return self._config.get(key.category, {}).get(key.key, None)
        elif isinstance(key, str):
            return self._config.get(key, None)

        raise TypeError("Invalid key type")

    def get_value_old(self, key: str) -> Any:
        """Get the config value for the key. If key does not exist,
        None will return

        Args:
            key (str): config key

        Returns:
            Any: value for the key. None if key is not found
        """
        if key in self._config:
            return self._config[key]
        return None

    def get_drones(self) -> dict:
        """Get all the drones setting from the config
        """
        return self._config['drone']

    def get_logging_value(self, key: str) -> Any:
        """Get the config value for the logging key. If key does not exist,
        None will return

        Args:
            key (str): config key for logging

        Returns:
            Any: value for the key. None if key is not found
        """
        if key in self._config['logging']:
            return self._config['logging'][key]
        return None

    def get_server_value(self, key: str) -> Any:
        """Get the config value for the server key. If key does not exist,
        None will return

        Args:
            key (str): config key for server

        Returns:
            Any: value for the key. None if key is not found
        """
        if key in self._config['server']:
            return self._config['server'][key]
        return None

    def get_gui_value(self, key: str) -> Any:
        """Get the config value for the gui key. If key does not exist,
        None will return

        Args:
            key (str): config key for gui

        Returns:
            Any: value for the key. None if key is not found
        """
        if key in self._config['gui']:
            return self._config['gui'][key]
        return None

    def _get_config(self,) -> dict:
        """Convert the config file to dist. It also validate the config,

        Raises:
        FileNotFoundError: config file not found

        Returns:
            dict: config file in python dictionary
        """
        with open(self.config_file, "rb") as file:
            config = tomli.load(file)
            return config
        
    def _validate_key(self,source:dict ,key: ConfigKey, required: bool = True) -> bool:
        """Generic function to validate the key. If the key is required: if the key not found, 
        error message will be added and return `False`. If the key is not required: only 

        Args:
            source (dict): _description_
            key (ConfigKey): _description_
            required (bool, optional): _description_. Defaults to True.

        Returns:
            bool: _description_
        """
        if key.category not in source:
            if required:
                self._error_msg.append(ConfigErrorMessage(logging.WARNING, f"{key.category} is not found in config file"))
            return False
        
        
        if key.key not in source[key.category] or not isinstance(source[key.category][key.key], key.type):
            if required:
                self._error_msg.append(ConfigErrorMessage(logging.WARNING, f"{key} is not found in config file"))
            return False
        self._config[key.category][key.key] = source[key.category][key.key]
        
        return True
        
        

    def _config_validation(self, source: dict):
        """Validate the config dictionary. If some key does not valid, but it can be ignored or use
        default value. If critical error, None is return. The program can check using
        `is_critical()`

        Args:
            source (dict): config dict read from config file

        """
        # print(config)
        logging_key = "logging"
        gui_key = "gui"
        server_key = "server"
        drone_key = "drone"

        logging_level = {
            'INFO': logging.INFO,
            'DRONE': LOGGER_LEVEL_DRONE,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'DEBUG': logging.DEBUG
        }

        if not source or not isinstance(source, dict):
            raise ConfigError(ErrorMessage.INVALID_FILE.value)

        if drone_key not in source:
            raise ConfigError(
                ErrorMessage.INVALID_VALUE.value % drone_key)

        self._config = deepcopy(DEFAULT_CONFIG)
        
        
        # root level
        
        self._config['debug'] = source.get('debug', False)
        
        self._config['dump_flight_data'] = source.get('dump_flight_data', False)
        

        # use drone temp to avoid dictionary changed size during iteration error
        # Validate drone
        for key, drone in list(source[drone_key].items()):
            if ConfigKey.DRONE_ENABLE.key in drone:
                if not isinstance(drone[ConfigKey.DRONE_ENABLE.key], ConfigKey.DRONE_ENABLE.type):
                    self._error_msg.append(
                        (WARNING, ErrorMessage.INVALID_VALUE.value % (ConfigKey.DRONE_ENABLE,)))
                    del drone[ConfigKey.DRONE_ENABLE.key]
                elif not drone[ConfigKey.DRONE_ENABLE.key]:
                    continue

            if 'name' not in drone:
                drone['name'] = key
                self._error_msg.append(
                    (WARNING, ErrorMessage.INVALID_VALUE_CUSTOM.value % (f"drone.{key}.name", key)))
            elif not isinstance(drone['name'], str):
                drone['name'] = str(drone['name'])

            # Missing uri for the drone. Skipping this drone
            if 'uri' not in drone:
                self._error_msg.append((WARNING, ErrorMessage.INVALID_VALUE_CUSTOM.value % (
                    f"drone.{key}.uri", "Skipping this drone")))
                continue
            elif not isinstance(drone['uri'], str):
                drone['uri'] = str(drone['uri'])

            if 'stream' not in drone:
                self._error_msg.append((WARNING, ErrorMessage.INVALID_VALUE_CUSTOM.value % (
                    f"drone.{key}.stream", "Skipping this drone")))
                continue
            elif not isinstance(drone['stream'], str):
                drone['stream'] = str(drone['stream'])

            self._config['drone'][key] = drone

        if logging_key not in source:
            self._error_msg.append((WARNING, ErrorMessage.INVALID_VALUE.value % (
                logging_key,)))
        # Validate log variable
        else:
            config_logging = source[logging_key]
            # logging.enable
            # if 'enable' in config_logging:
            #     if not isinstance(config_logging['enable'], bool):
            #         self._error_msg.append(
            #             ConfigErrorMessage(WARNING,
            #                                ErrorMessage.INVALID_VALUE.value % (logging_key+'.enable',)))
            #     else:
            #         config[logging_key]['enable'] = config_logging['enable']
            self._validate_key(source, ConfigKey.LOGGING_ENABLE)
            # logging.level, only check if logging is enabled
            if self._config[logging_key]['enable']:
                # Invalid logging level use default
                if 'level' in config_logging:

                    if not isinstance(config_logging['level'], str) or \
                            config_logging['level'].upper() not in ['DEBUG', 'DRONE', 'INFO', 'WARNING', 'ERROR']:
                        self._error_msg.append(
                            ConfigErrorMessage(WARNING,
                                               ErrorMessage.INVALID_VALUE.value % (logging_key+'.level', )))
                    else:
                        self._config[logging_key]['level'] = logging_level[config_logging['level'].upper(
                        )]

                # logging.log_file
                self._validate_key(source, ConfigKey.LOGGING_LOG_FILE)

        # GUI
        if gui_key in source:
            self._validate_key(source, ConfigKey.GUI_DEBUG, required=False)
        

            self._validate_key(source, ConfigKey.GUI_SHOW_ON_START, required=False)

        # Server config
        if server_key in source:
            # server.enable
            self._validate_key(source, ConfigKey.SERVER_ENABLE)
            # server.host
            if self.server_enable:
                if not self._validate_key(source, ConfigKey.SERVER_HOST):
                    self._config[server_key]['enable'] = False
                    return 
            

            # server.port
            if self._config[server_key]['enable']:
                if not self._validate_key(source, ConfigKey.SERVER_PORT):
                    self._config[server_key]['enable'] = False
                    return

            # server.log_file
            if self._config[server_key]['enable']:
                self._validate_key(source, ConfigKey.SERVER_LOG_FILE, required=False)

            # server.debug
                self._validate_key(source, ConfigKey.SERVER_DEBUG, required=False)

    @property
    def logging_enable(self) -> bool:
        return self._config['logging']['enable']

    @property
    def server_enable(self) -> bool:
        return self._config['server']['enable']

    def to_json(self, indent: int | None = None) -> str:
        """to_json for jsonpickle 

        Args:
            indent (int, optional): indentation for the json string. Defaults to None.

        Returns:
            str: Config in json format. Contain all the config
        """
        return json.dumps(self._config, indent=indent)

    def __getstate__(self) -> dict:
        """_summary_ for jsonpickle 

        Returns:
            dict: Config in json format. Contain all the config
        """
        return self._config

    def __str__(self) -> str:
        """print out the details of the config file

        Returns:
            str: Config file details
        """
        return f"config file: {self.config_file}\nconfig: {self._config}"

    def __repr__(self) -> str:
        """print out the details of the config file

        Returns:
            str: Config file details
        """
        return f"config file: {self.config_file}\nconfig: {self._config}"
