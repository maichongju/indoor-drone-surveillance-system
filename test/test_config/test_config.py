from importlib.resources import path
from testfixtures import LogCapture
import tomli

import logging
from config.config import Config, ConfigCategory, ConfigError, DEFAULT_CONFIG, ConfigKey

import pytest

CONFIGROOT = "test/test_config/configs/"


def get_path(filename: str) -> str:
    return CONFIGROOT + filename


class TestConfig:

    @pytest.fixture
    def default_config(self):
        path = get_path('default_config.toml')
        with open(path, 'rb') as f:
            config = tomli.load(f)
            config['logging']['level'] = logging.DEBUG
            return config

    @pytest.fixture
    def config(self):
        path = get_path('default_config.toml')
        return Config(path)

    def test_get_value_with_config_key(self, default_config, config):
        for key in ConfigKey:
            if key.category_raw == ConfigCategory.DRONE:
                with pytest.raises(ValueError):
                    config.get_value(key)
                continue
            assert config.get_value(
                key) == default_config[key.category][key.key]

    def test_get_value_with_category(self, default_config, config):
        for category in ConfigCategory:
            result = config.get_value(category)
            assert result == default_config.get(category.name)


class TestConfigLogging:
    def test_invalid_file_path(self):
        path = 'invalid path'
        with pytest.raises(FileNotFoundError):
            Config(path)

    def test_missing_logging(self):
        path = get_path('logging_missing.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno == logging.WARNING
            assert config.get_value_old('logging') == DEFAULT_CONFIG['logging']

    def test_missing_logging_enable(self):
        path = get_path('logging_enable_missing.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno == logging.WARNING
            assert config.get_logging_value(
                'enable') == DEFAULT_CONFIG['logging']['enable']

    def test_invalid_logging_enable(self):
        path = get_path('logging_enable_missing.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno == logging.WARNING
            assert config.get_logging_value(
                'enable') == DEFAULT_CONFIG['logging']['enable']

    def test_missing_logging_level(self):
        path = get_path('logging_level_missing.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno == logging.WARNING
            assert config.get_logging_value(
                'level') == DEFAULT_CONFIG['logging']['level']

    def test_invalid_logging_level(self):
        path = get_path('logging_level_invalid.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno, logging.WARNING
            assert config.get_logging_value(
                'level') == DEFAULT_CONFIG['logging']['level']

    def test_missing_logging_file_name(self):
        path = get_path('logging_file_name_missing.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert config.get_logging_value(
                'log_file') == DEFAULT_CONFIG['logging']['log_file']

    def test_invalid_logging_file_name(self):
        path = get_path('logging_file_name_invalid.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno == logging.WARNING
            assert config.get_logging_value(
                'log_file') == DEFAULT_CONFIG['logging']['log_file']


class TestConfigServer:

    def test_missing_server(self):
        path = get_path('server_missing.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert len(l.records) == 0
            assert config.get_server_value(
                'enable') == DEFAULT_CONFIG['server']['enable']

    def test_missing_server_enable(self):
        path = get_path('server_enable_missing.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno, logging.WARNING
            assert config.get_server_value(
                'enable') == DEFAULT_CONFIG['server']['enable']

    def test_invalid_server_enable(self):
        path = get_path('server_enable_invalid.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno == logging.WARNING
            assert config.get_server_value(
                'enable') == DEFAULT_CONFIG['server']['enable']

    def test_missing_server_host(self):
        path = get_path('server_host_missing.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno == logging.WARNING
            assert config.get_server_value(
                'enable') == False

    def test_invalid_server_host(self):
        path = get_path('server_host_invalid.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno == logging.WARNING
            assert config.get_server_value(
                'enable') == False

    def test_missing_server_port(self):
        path = get_path('server_port_missing.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno == logging.WARNING
            assert config.get_server_value(
                'enable') == False

    def test_invalid_server_port(self):
        path = get_path('server_port_invalid.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno == logging.WARNING
            assert config.get_server_value(
                'enable') == False

    def test_missing_server_debug(self):
        path = get_path('server_debug_missing.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert len(l.records) == 0
            assert config.get_server_value(
                'debug') == DEFAULT_CONFIG['server']['debug']

    def test_invalid_server_debug(self):
        path = get_path('server_debug_invalid.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno == logging.WARNING
            assert config.get_server_value(
                'debug') == DEFAULT_CONFIG['server']['debug']

    def test_missing_server_log_file(self):
        path = get_path('server_log_file_missing.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert len(l.records) == 0
            assert config.get_server_value(
                'log_file') == DEFAULT_CONFIG['server']['log_file']

    def test_invalid_server_log_file(self):
        path = get_path('server_log_file_invalid.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno == logging.WARNING
            assert config.get_server_value(
                'log_file') == DEFAULT_CONFIG['server']['log_file']


class TestConfigDrone():
    def test_valid_drone(self):
        path = get_path('valid_config.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert len(l.records) == 0
            drone = {
                "drone1": {
                    "name": "drone1",
                    "uri": "radio://0/80/2M/E7E7E7E702",
                    "stream": "192.168.0.1"
                },
                "drone2": {
                    "name": "drone2",
                    "uri": "radio://0/80/2M/E7E7E7E703",
                    "stream": "192.168.0.1"
                }
            }
            assert config.get_drones() == drone

    def test_missing_drone(self):
        path = get_path('drone_missing.toml')
        with pytest.raises(ConfigError):
            Config(path)

    def test_missing_drone_name(self):
        path = get_path('drone_name_missing.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno == logging.WARNING
            assert config.get_drones()['drone1']['name'] == 'drone1'

    def test_invalid_drone_name(self):
        path = get_path('drone_name_invalid.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert len(l.records) == 0
            assert config.get_drones()['drone1']['name'] == '123456'

    def test_disable_drone(self):
        path = get_path('drone_disable.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert len(l.records) == 0
            assert len(config.get_drones()) == 0

    def test_missing_uri(self):
        path = get_path('drone_uri_missing.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno == logging.WARNING
            assert len(config.get_drones()) == 0

    def test_missing_stream(self):
        path = get_path('drone_stream_missing.toml')
        with LogCapture() as l:
            config = Config(path)
            config.display_error_messages()
            assert l.records[0].levelno == logging.WARNING
            assert len(config.get_drones()) == 0
