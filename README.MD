# Drone System Base Station (DSBS)

## Prerequisites

To run the program, python 3.10 or later is required. `requirements.txt` contains the required packages. Use `pip install -r requirements.txt` to install the packages.

## Submodules

- [cflib](https://github.com/bitcraze/crazyflie-lib-python) `cflib` is the library used to communicate with the Crazyflie.
- [yolov5](https://github.com/ultralytics/yolov5)

### `yolov5`

`yolov5` is one of the object detection library used to detect objects in the image. It is a modified version of the original `yolov5` library. The original `yolov5` library have its own logging handler where it is interfering the logging format of the project. `set_logging()` function in `yolov5/utils/general.py` is comment out to disable the additional logging handler.

Special thanks to the follow thread for the help:

- https://www.pythonguis.com/tutorials/multithreading-pyqt6-applications-qthreadpool/

## Configuration

Customize the configuration file `config.toml` to fit your needs. [Configuration](docs/config.md) contain the details of the configuration.

## REST API

The application also contain a REST API that can be used to communicate with the software. More detail for the API can be find [here](docs/web/README.md).

## Onboard Camera

Detail of onboard camera can be found [here](pi-camera/readme.md).