from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

from copy import deepcopy

import logging

from . import LOGGER_LEVEL_DRONE


from config import Config

log_format = '%(asctime)s %(levelname)s %(message)s'
date_format = '%Y-%m-%d %H:%M:%S'

formatter = logging.Formatter(fmt=log_format,
                              datefmt=date_format)

LOGGER = logging.getLogger("droneServer")
WEBLOGGER = logging.getLogger("werkzeug")


def logging_init(config: Config) -> None:
    """init for logging. if log file name is given, the logging will also output to the
    file.

    Args:
        config (Config): config file
    """
    _addLoggingLevel('DRONE', LOGGER_LEVEL_DRONE)
    handler = [logging.StreamHandler()]

    if config.logging_enable and config.get_logging_value('file_name') is not None:
        file_handler = logging.FileHandler(
            config.get_logging_value('file_name'),
            encoding='utf-8')
        file_handler.setFormatter(formatter)
        LOGGER.addHandler(file_handler)

    if config.server_enable and config.get_server_value('log_file') is not None:
        file_handler = logging.FileHandler(
            config.get_server_value('log_file'),
            encoding='utf-8')
        file_handler.setFormatter(formatter)
        WEBLOGGER.addHandler(file_handler)

    LOGGER.setLevel(config.get_logging_value('level'))

    handler.append(logging.FileHandler('log.log'))

    logging.basicConfig(
        level=config.get_logging_value('level'),
        format=log_format,
        datefmt=date_format,
        handlers=handler
    )

# https://stackoverflow.com/questions/2183233/how-to-add-a-custom-loglevel-to-pythons-logging-facility/35804945#35804945


def _addLoggingLevel(levelName, levelNum, methodName=None):
    """
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `levelName` becomes an attribute of the `logging` module with the value
    `levelNum`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present 

    Example
    -------
    >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5

    """
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
        raise AttributeError(
            '{} already defined in logging module'.format(levelName))
    if hasattr(logging, methodName):
        raise AttributeError(
            '{} already defined in logging module'.format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
        raise AttributeError(
            '{} already defined in logger class'.format(methodName))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)

    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)


def get_global_logger_level() -> int:
    """Get the global logger level

    Returns:
        int: global logger level
    """
    return logging.getLogger().getEffectiveLevel()
