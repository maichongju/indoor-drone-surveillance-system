# Configuration

`config.toml` contain the configuration setting for the application. The configuration contain the following different sections:

- [`Global`](#global)
- [`Drone`](#drone)
- [`Logging`](#logging)
- [`GUI`](#gui)
- [`Server`](#server)


## Global

This setting is for the global setting

- debug (bool, optional): Enable debug mode. Default: `false`
- dump_flight_data (bool, optional): Dump flight data to csv files. The flight data are named based on the time of flight. Each take off will generate a new log file. All the log files will save in `/logs/flight` Default: `false`


## Drone

Contain all the drone configuration. Each drone contain the following fields:

- name (string): name of the drone
- uri (string): URI of the drone
- stream (string): video stream url
- enable (bool, optional): enable or disable the drone (default: true)

When new drone added, ensure to use a new drone number. `[drone.droneXX]` XX is the drone number, make sure the number is unique and it is under the previous drone.

## Logging

Define the logging behavior of the server (Not GUI)

- enable (bool, optional): enable or disable the logging (default: false)
- level (string, optional): log level (default: "INFO")
- file (string, optional): log file path (default: "logs/client.log")

## GUI

- debug (bool, optional): enable or disable the debug mode (default: false)

## Server

Contain the setting for web server.

- enable (bool): enable or disable the server
- host (string): host address of the server
- port (int): port number of the server
- log_file (string, optional): log file path (default: "logs/server.log")
- debug (bool, optional): enable or disable debug mode
