from typing import Any

import jsonpickle
from config.config import Config
from flask import Flask, Response, abort, request
from hub.hub import Hub
from log.logger import WEBLOGGER
from werkzeug.exceptions import HTTPException

from www import HTTPStatus, WebError
from general.utils import validate_ip


class FlaskApp():
    app = None

    def __init__(self, config: Config, hub: Hub):
        self.app = Flask(__name__)
        self._config = config
        self._hub = hub
        self._debug = self._config.get_server_value('debug')
        self.setup_error_handler()
        self.setup_end_point()
        self.setup_debug_end_point()

    def setup_error_handler(self):
        """Register all the basic error handler
        """
        for status in HTTPStatus:
            if status.value >= 400:
                try:
                    self.app.register_error_handler(
                        status.value, self._error_handler)
                except Exception as e:
                    WEBLOGGER.debug(f"{status.value} not registered")

    def _error_handler(self, error: HTTPException):
        """Return a response base on the error.
        """
        status = HTTPStatus.get_status_by_code(error.code)
        return self.make_response(None, status, error)

    def setup_end_point(self):
        self.add_end_point('/', 'index', self.index)
        self.add_end_point('/drones', 'drones', self.drones)
        self.add_end_point('/drone/<drone_id>', 'get_drone', self.get_drone)
        self.add_end_point('/camera/low_battery', 'low_battery', self.onboard_camera_low_battery, methods=['POST'])

    def setup_debug_end_point(self):
        self.add_end_point('/debug/status/<int:code>',
                           'debug_status_code', self.debug_status_code)

    def debug_status_code(self, code: int):
        if not self._debug:
            return self.response_debug_not_enable()
        if HTTPStatus.get_status_by_code(code) is None:
            abort(404)
        abort(code)

    def index(self):

        return self.make_response("Web Server is working!")

    def drones(self):
        """
        End point function for drones.
        """
        args = request.args

        if args.get('basic', type=bool):
            return self.make_response(self._hub.get_basic_info())

        return self.make_response(self._hub)

    def get_drone(self, drone_id: str):
        return self.make_response(f"{drone_id}")

    def add_end_point(self, end_point: str, end_point_name: str, handler: callable, **kwargs):
        self.app.add_url_rule(end_point, end_point_name, handler, **kwargs)

    def make_response(self, data: Any,
                      status: HTTPStatus = HTTPStatus.OK,
                      error: WebError | HTTPException = None) -> Response:
        """Create a response base on the status and error. Response also contain the status code
        for the response. If it is `200`, data block is contain the actual response data. If `error` 
        is provided, it use `error` to create the response. If `status` >= 400 and no `error` 
        is provided, it use default status phrase as error message. All the error information is 
        stored in `error` block.

        Args:
            data (Any): Any data. Must be serializable by `jsonpickle`.
            status (HTTPStatus, optional): response status. Defaults to HTTPStatus.OK.
            error (WebError, optional): error message. Defaults to None.
        """
        default_mimetype = 'application/json'
        d = {'status': status.value}
        if error is None:
            try:
                # Try to jsonfy the data
                d['data'] = data
                return Response(jsonpickle.encode(d, unpicklable=False),
                                status=status.value,
                                mimetype=default_mimetype)
            except Exception as e:
                # Internal error, possible due to invalid data
                error = WebError.INTERNAL_SERVER_ERROR
                status = HTTPStatus.INTERNAL_SERVER_ERROR
                WEBLOGGER.exception(e)

        # use two if statements to ensure the error of processing can be handled
        if error is not None:
            d['error'] = {
                'code': str(error.code),
                'desc': error.description
            }
        elif status >= HTTPStatus.BAD_REQUEST:
            # bad status but no error, use default phrase for the error
            d['error'] = {
                'code': str(status.value),
                'desc': status.phrase
            }

        return Response(jsonpickle.encode(d, unpicklable=False),
                        status=status.value,
                        mimetype=default_mimetype)

    def onboard_camera_low_battery(self):
        """end point for drone to notify the server that the onboard camera is low on battery.
        This endpoint only allow POST request.
        """
        ip: str = request.form.get('ip')
        if not validate_ip(ip):
            return self.make_response(None,
                                      status=HTTPStatus.BAD_REQUEST,
                                      error=WebError.INVALID_IP)
        self._hub.low_battery_notify(ip)
        return self.make_response(None, HTTPStatus.OK)

    def response_debug_not_enable(self):
        """Response for debug not enable
        """
        return self.make_response(None,
                                  status=HTTPStatus.BAD_REQUEST,
                                  error=WebError.DEBUG_NOT_ENABLE)

    def run(self):
        self.app.run(self._config.get_server_value('host'),
                     self._config.get_server_value('port'),
                     )
