from dataclasses import dataclass, field
from threading import Thread, Event
import cv2
from datetime import datetime

import jsonpickle

from log.logger import LOGGER

from cflib.utils.callbacks import Caller

from ml.objectdetection import ObjectDetection
from ml.objectdetection import Model
from ml.objectdetection import Result

from general.utils import get_ip_address


@dataclass
class StreamCallBacks:
    """Stream callbacks for drone

    invalid_stream: called when the stream is invalid.
    new_frame: called when a new frame is received. `np.ndarray` is passed to the callback.
    connection_lost: called when the connection is lost unexpectedly.
    stream_ended: called when the stream is ended.
    """

    """ Trigger when the stream in invalid. Parameter: `str`"""
    invalid_stream: Caller = field(default_factory=Caller, init=False)

    """ Trigger when new frame is received. Always call and return the original frame."""
    new_frame: Caller = field(default_factory=Caller, init=False)

    """Only trigger when object detection is enabled. It returns `Result` object"""
    new_frame_od_enabled: Caller = field(default_factory=Caller, init=False)

    # Only trigger when stream connection lost during streaming
    connection_lost: Caller = field(default_factory=Caller, init=False)

    # Trigger when stream connection closed
    stream_ended: Caller = field(default_factory=Caller, init=False)

    # any stream unexpected error. Parameter: `Exception`
    stream_error: Caller = field(default_factory=Caller, init=False)

    # Trigger when stream is started
    stream_started: Caller = field(default_factory=Caller, init=False)


class VideoStream:
    def __init__(self,
                 url: str,
                 resolution: tuple | list = (640, 480),
                 object_detection: bool = False,
                 model_setting: Model = Model.YOLOV5
                 ):
        self._url = url
        self._resolution = resolution
        self._model_setting = model_setting
        self._model = None
        self._object_detection_enable = object_detection
        self.callbacks = StreamCallBacks()
        self._stream = None
        self.od_result = None
        self.callbacks.new_frame_od_enabled.add_callback(self._od_callback)

    def _od_callback(self, result: Result):
        self.od_result = result.data if result is not None else None

    def start(self):
        """Start the stream. If this is the first time with object detection is enable,
        this will block the thread until the model is loaded. If the model fails to load,
        object detection will be disabled. 
        """
        # TODO Check if model changed, if change need to load the new model again
        if self._object_detection_enable and self._model is None:
            self._model = Model.getModel(self._model_setting)

        if self._stream is None or not self._stream.is_alive():
            self._stream = VideoStreamThread(
                self._url,
                self.callbacks,
                self._resolution,
                self._model,
                object_detection_enable=self._object_detection_enable)
        self._stream.start()

    def stop(self):
        """ Stop potentially blocking the thread
        """
        self._stream.stop()
        self._stream.join()

    def to_json(self, indent: int | None = None) -> str:
        """to_json for jsonpickle

        Returns:
            str: json representation of stream
        """
        return jsonpickle.encode(self.__getstate__(), unpicklable=False, indent=indent)

    def get_basic_info(self) -> dict:
        """Get the basic information of the stream. Including the following fields:
        - url: str
        - resolution: tuple
        """
        return {
            'url': self._url,
            'resolution': self._resolution
        }

    def __getstate__(self) -> dict:
        """pickle support
        """
        return {
            'url': self._url,
            'resolution': self._resolution,
            'object_detection': self.od_result
        }

    @property
    def object_detection_enable(self) -> bool:
        return self._object_detection_enable

    @object_detection_enable.setter
    def object_detection_enable(self, value: bool):
        """Update the object detection status. If is streaming, streaming thread will switch to 
        object detection mode right away. However, this could lower the frame rate base on the computer
        process power. If the stream is off, it will be enabled when the stream is started. 

        Args:
            value (bool): `True` to enable object detection, `False` to disable.
        """
        self._object_detection_enable = value
        if self._model is None and value and self._stream is not None and self._stream.is_alive():
            LOGGER.drone(
                'Object detection is enabled. But no model is loaded. Please stop the stream and load the model first.')
            return
        if self._stream is not None:
            self._stream.object_detection = value

    @property
    def url(self) -> str:
        return self._url

    @property
    def is_streaming(self) -> bool:
        return self._stream.is_streaming if self._stream is not None else False

    @property
    def model_init(self) -> bool:
        """Determine if the model is initialized.
        """
        return self._model is not None

    @property
    def ip(self) -> str:
        if self._url is None:
            return ''
        return get_ip_address(self._url)


@dataclass
class _VideoStreamWarningFlag:
    object_detection_no_available: bool = False

    def reset(self):
        self.object_detection_no_available = False


class VideoStreamThread(Thread):
    """VideoStreamThread is a thread that continuously receives frames from the drone.
    """

    def __init__(self,
                 url: str,
                 callbacks: StreamCallBacks,
                 resolution: tuple,
                 _model: ObjectDetection,
                 object_detection_enable: bool = False):
        super().__init__()
        if url.lower() == 'camera':
            self._url = 0
        else:
            self._url = url
        self._warning_flag = _VideoStreamWarningFlag()
        self._resolution = resolution
        self._callbacks = callbacks
        self._stop_stream = False
        self._object_detection_enable = object_detection_enable
        self._model = _model
        self._created_time = datetime.now()
        self._start_notify = Event()

    def run(self):
        try:
            LOGGER.debug(f"Opening Stream for {self._url}")
            stream = cv2.VideoCapture(self._url)

            if not stream.isOpened():
                LOGGER.warning(f"Cannot open stream ({self._url})")
                self._callbacks.invalid_stream.call(str(self._url))
                return

            LOGGER.debug(f"Stream opened for {self._url}")
            LOGGER.debug(f"Setting resolution to {self._resolution}")

            stream.set(cv2.CAP_PROP_FRAME_WIDTH, self._resolution[0])
            stream.set(cv2.CAP_PROP_FRAME_HEIGHT, self._resolution[1])
            # Only get the latest frame
            stream.set(cv2.CAP_PROP_BUFFERSIZE, 0)
            while not self._stop_stream:
                # Stream connection lost
                if not stream.isOpened():
                    LOGGER.warning(f"Stream connection lost {self._url}")
                    self._callbacks.connection_lost.call()
                    break
                ret, frame = stream.read()
                if not ret:
                    LOGGER.warning(f"Stream connection lost {self._url}")
                    self._callbacks.connection_lost.call()
                    break
                if not self._start_notify.is_set():
                    self._start_notify.set()
                    self._callbacks.stream_started.call()
                # * Object detection off or model is None
                if self._object_detection_enable and self._model is not None:
                    _frame = self._model.detect(
                        frame, plot_boxes=True, plot_text=True)
                    self._callbacks.new_frame_od_enabled.call(_frame)
                self._callbacks.new_frame.call(frame)
            stream.release()
        except AttributeError as e:
            #! Application is closed before stream is closed
            LOGGER.debug(
                f"Program closed before shutting down stream ({self._url})")
        except Exception as e:
            LOGGER.debug(f"Stream error {e}")
            LOGGER.error(f"Stream error for {self._url}")
            self._callbacks.stream_error.call(e)
        finally:
            try:
                self._callbacks.stream_ended.call()
                LOGGER.debug(f"Stream ended for {self._url}")
            except AttributeError:
                #! Application is closed before stream is closed
                LOGGER.debug(
                    f"Program closed before shutting down stream ({self._url})")

    def stop(self):
        self._stop_stream = True

    @property
    def is_streaming(self):
        return not self._stop_stream

    @property
    def object_detection(self) -> bool:
        return self._object_detection_enable

    @object_detection.setter
    def object_detection(self, value: bool):
        self._object_detection_enable = value

    def __repr__(self) -> str:
        created_time = self._created_time.strftime("%Y-%m-%d %H:%M:%S")
        return super().__repr__() + f"({self._url}, {created_time})"
