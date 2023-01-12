from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import cv2
import numpy as np
import torch

from log.logger import LOGGER

cache_dir = "ml/models/cache"
model_dir = "ml/models/"


@dataclass
class ObjectRecord:
    """Object Record for each entity. This including the label 
    name, coordinates, confidence score.
    """
    name: str
    x1: float
    y1: float
    x2: float
    y2: float
    prob: float

    def __init__(self, name: str, x1: float, y1: float, x2: float, y2: float, prob: float):
        self.name = str(name)
        self.x1 = float(x1)
        self.y1 = float(y1)
        self.x2 = float(x2)
        self.y2 = float(y2)
        self.prob = float(prob)

    def __getstate__(self) -> dict:
        print(type(self.x1))
        return self.__dict__


class FrameResult:
    """Convert the raw data into more structure data. `FrameResult.data` contain the following 
    structure:
        {
            'class_name': [`ObjectRecord`]
        }
    """

    def __init__(self,
                 threshold: float,
                 classes: list,
                 label: list,
                 cord: list):
        self._data = self._process_data(classes, label, cord)

    def _process_data(self, classes: list, labels: list, cords: list) -> dict:
        """Process the raw data to a dictionary

        Args:
            classes (list): list of class names
            label (list): list of labels
            cord (list): list of coordinates

        Returns:
            dict: dictionary of class name and coordinates
        """
        data = {}
        class_size = len(classes)
        for label, cord in zip(labels, cords):
            class_index = int(label)
            # for some reason the label is out of range. Ignore it.
            if class_index >= class_size:
                continue

            class_name = classes[class_index]
            if class_name not in data:
                data[class_name] = []
            data[class_name].append(ObjectRecord(
                class_name,
                cord[0], cord[1],
                cord[2], cord[3],
                cord[4]
            ))
        return data

    def get_class_list(self, key: str) -> list(ObjectRecord):
        """get the class name from the model result. Case insensitive.

        Args:
            key (str): class name

        Returns:
            list(ObjectRecord): list of object record
        """
        return self._data.get(key.lower(), None)

    def __getstate__(self) -> dict:
        return self.data

    @property
    def data(self) -> dict:
        return self._data


@dataclass(frozen=True)
class Result:
    """Contain the detecting result from the model
    """
    data: FrameResult
    frame: np.ndarray


@dataclass
class _Model:
    name: str
    local_file: str
    local_dir: str
    description: str | None = None

    def __init__(self, name: str, local_file: str, local_weights_dir: str, description: str = None, show_class: list = []):
        self.name = name
        self.local_file = f"{model_dir}{local_file}"
        self.local_dir = f"{model_dir}{local_weights_dir}"
        self.description = description
        self.show_class = show_class

    def __getstate__(self) -> dict:
        return {
            'name': self.name,
            'description': self.description,
        }


class Model(Enum):
    """ <model name>, <model file>, <model directory if any>  """
    YOLOV5 = _Model(name='yolov5s',
                    local_file='yolov5s.pt',
                    local_weights_dir='yolov5',
                    show_class=[0])

    @staticmethod
    def getModel(model: Model) -> ObjectDetection:
        """Create a Object Detection model based on the `model`

        Args:
            model (Model): model need to be loaded

        Returns:
            ObjectDetection: `ObjectDetection` model. Check `error` to see if the model is loaded successfully.
        """
        if not isinstance(model, Model):
            return None
        match model:
            case Model.YOLOV5:
                return ObjectDetection(model)

    def __repr__(self) -> str:
        return self.value.__repr__()


@dataclass
class _ObjectDetectionWarningFlag:
    detect_model_init_error: bool = False

    def reset(self):
        self.detect_model_init_error = False


class ObjectDetection:
    """Object Detection. It use `cuda` if available, otherwise use `cpu`
    """

    def __init__(self, model: Model):
        self._model_setting = model

        # determine if cuda is available
        self._device = 'cuda' if torch.cuda.is_available() else 'cpu'
        LOGGER.debug(f"Device: {self._device}")

        self._warning_flag = _ObjectDetectionWarningFlag()

        self._error = False

        # Set up model download cache directory
        torch.hub.set_dir(cache_dir)

        self._model = self._load_model(model)

    def _load_model(self, model_setting: Model) -> Any:
        """Load the model from the `Model`. This will try to load 
        the model from online, if that is not available it will try
        to load the local cache.

        Args:
            model_setting (Model): Model need to be loaded

        Returns:
            Any: machine learning model
        """
        model = None
        match model_setting:
            case Model.YOLOV5:
                try:
                    model = torch.hub.load(
                        model_setting.value.local_dir,
                        'custom',
                        path=model_setting.value.local_file,
                        source='local',
                    )
                    LOGGER.debug(f"Model loaded: {model_setting.value.name}")
                except ModuleNotFoundError as e:
                    self._error = True
                    LOGGER.debug(f"[ObjectDetection] Online: {type(e)}{e}")
                    LOGGER.error(
                        "Loading object detection model failed. Have you install all thr required package?")
                except Exception as e:
                    LOGGER.debug(f"[ObjectDetection] Online: {type(e)}{e}")
                    LOGGER.warning(
                        f"Loading model({model_setting.value.name}) from online failed. Trying load from local.")
                finally:
                    if not self._error:
                        self._classes = model.names
        return model

    def _score_frame(self, frame: np.ndarray, threshold: float) -> FrameResult:
        """Score the frame with the model

        Args:
            frame (_type_): frame to be scored
            threshold (float): threshold to filter the result

        Returns:
            FrameResult: result of the frame
        """
        match self._model_setting:
            case Model.YOLOV5:
                self._model.to(self._device)
                frame = [frame]
                results = self._model(frame)
                if self._device == 'cuda':
                    labels, cord = results.xyxyn[0][:, -1].detach().to(
                        'cpu').numpy(), results.xyxyn[0][:, :-1].detach().to('cpu').numpy()
                else:
                    labels, cord = results.xyxyn[0][:, -
                                                       1].numpy(), results.xyxyn[0][:, :-1].numpy()
                # * label : [label]
                # * cord : [x1, y1, x2, y2, prob]
                return FrameResult(threshold, self._classes, labels, cord)

    def plot_boxes(self,
                   frame: np.ndarray,
                   results: FrameResult,
                   frame_color: tuple = (0, 0, 255),
                   plot_text: bool = False,
                   plot_text_color: tuple | None = None
                   ) -> np.ndarray:
        """_summary_

        Args:
            results (FrameResult): result to be plotted
            frame (np.ndarray): frame to be plotted
            frame_color (tuple, optional): frame color. Defaults to (255, 0, 0).
            plot_text (bool, optional): Should plot text or not. Defaults to False.
            plot_text_color (tuple, optional): Color of the text. If is `None`, then 
                it will use the same color as frame. Defaults to None.

        Returns:
            np.ndarray: frame with boxes plotted or text plotted
        """
        # Need to convert to bgr (tuple dont have reverse)
        color = list(frame_color)
        color.reverse()
        text_color = color
        if plot_text_color is not None:
            text_color = plot_text_color.reversed()

        x_shape, y_shape = frame.shape[1], frame.shape[0]

        for records in results.data.values():
            for record in records:
                if record.name.lower() != 'person':
                    continue
                x1, y1 = int(record.x1 * x_shape), int(record.y1 * y_shape)
                x2, y2 = int(record.x2 * x_shape), int(record.y2 * y_shape)
                cv2.rectangle(frame,
                              (x1, y1), (x2, y2), frame_color, 2)

                if plot_text:
                    cv2.putText(frame, record.name, (x1, y1),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 1)
        return frame

    def detect(self, frame: np.ndarray,
               plot_boxes: bool = False,
               plot_color: tuple = (255, 0, 0),
               plot_text: bool = False,
               threshold: float = 0.6) -> Result:
        """Detect the object in the frame.

        Args:
            frame (np.ndarray): frame to detect
            plot_boxes (bool): if True, plot the boxes on the frame
            plot_color (tuple): color of the boxes. in RGB
            threshold (float): threshold to determine if the object is detected. Default to 0.6
        """
        frame = np.copy(frame)
        if self.error:
            if not self._warning_flag.detect_model_init_error:
                LOGGER.warning(
                    "Model initialization failed. Please check the model.")
                self._warning_flag.detect_model_init_error = True
            return Result([], frame)
        frame_result = self._score_frame(frame, threshold)
        if plot_boxes:
            frame = self.plot_boxes(
                frame, frame_result, plot_color, plot_text=plot_text)
        return Result(frame_result, frame)

    def __repr__(self) -> str:
        s = {
            "model": self._model_setting.value.name,
            "file_name": self._model_setting.value.local_file,
            "model directory": self._model_setting.value.local_weights_dir,
        }
        return str(s)

    @property
    def error(self) -> bool:
        return self._error
