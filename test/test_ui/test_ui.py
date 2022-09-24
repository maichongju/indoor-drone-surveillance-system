import pytest

import pytestqt
from hub.hub import Hub

from server import Server
from config import Config
from ui.GUI import GUI, MainWindow
from log.logger import logging_init

@pytest.fixture
def gui(qtbot:pytestqt.qtbot.QtBot):
    config = Config()
    logging_init(config)
    hub = Hub(config)
    mainWindow = MainWindow(hub)
    print(type(qtbot))
    qtbot.addWidget(mainWindow)
    return mainWindow

class TestUI():
    def test_ui(self, gui:GUI):
        pass