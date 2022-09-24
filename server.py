import sys
import logging
from threading import Thread

# General lib
from config import Config
from hub.hub import Hub
from log.logger import logging_init
from www.web import FlaskApp
from ui.GUI import GUI
from log.logger import LOGGER


class Server:

    def __init__(self, config: Config) -> None:
        self._config = config
        self._hub = Hub(config)
        if config.get_server_value('enable'):
            self._start_web_server()
        else:
            LOGGER.info('Web Server Disabled')

        self.gui = GUI(self._hub, config=config, start_check=False)
        self._start_GUI()
        # self._hub.drone.start()

    def _start_GUI(self):
        self.gui.exec()

    def _start_web_server(self):
        app = FlaskApp(self._config, self._hub)
        Thread(target=app.run, daemon=True).start()


if __name__ == "__main__":

    try:
        try:
            config = Config()
        except Exception as e:
            print(e)
            exit(1)
        logging_init(config)

        server = Server(config)
    except BaseException:
        LOGGER.exception("Error")
        raise
    # os._exit(0)
    sys.exit(0)
