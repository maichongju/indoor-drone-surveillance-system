# Drone

Each drone class contain a `Crazyflie` object from `cflib`, where the `Crazyflie` in charge to communicate with the drone.

## Fly Control


### Debug 

To enable `Debug` mode, add `debug=True` to the root of `config.toml`. 

#### Align to direction

Ensure the fly mode is set to `Normal`. Then select the `Align to direction` button. 

> https://plantuml.com/activity-diagram-beta

### Basic Setting

Some setting are hardcoded in the code. These configuration are essential for the drone to perform hover and auto avoid.

> Unit for velocity: m/s, distance: m, angle: degree. For velocity (vx, vy, vz, yaw). For distance (x, y, z)

- Auto avoid:

  - `auto_avoidance_velocity`: (0.15, 0.15, 0.15, 0)
  - `auto_avoidance_trigger_distance`: (0.3, 0.3, 0.2)
  - `auto_avoidance_min_distance`: Distance for drone to reach max avoid velocity. (0.15, 0.15, 0.15)

- Hover:
  - `hover_correction_min_distance`: (0.02, 0.02, 0.02)
  - `hover_correction_max_distance`: (0.05, 0.05, 0.05)
  - `hover_min_correction_velocity`: (0.02, 0.02, 0.02, 0)
  - `hover_max_correction_velocity`: (0.05, 0.05, 0.05, 0)

## Firmware

To find the firmware version of the `bin` file. Open the `bin` file with a hex editor and search for `stop_firmware`
