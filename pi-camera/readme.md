
This document walk through the basic configuration of the Raspberry Pi. The Raspberry pi install with Rasp OS.

There are three steps to set up the Raspberry Pi:

- Set up the wireless network
- Set up camera streaming server
- Set up battery monitor system


## Wireless network

1. Search for the wireless interface

```shell
$ ls /sys/class/net
eth0 wlan0
```

2. Locate `netplan` configuration file.

```shell
ls /etc/netplan
```

3. Edit the Netplan configuration file.

```shell
sudoedit /etc/netplan/50-cloud-init.yaml
```

Insert the following lines below network

```text
    wifis:
        wlan0:
            optional: true
            access-points:
                "SSID-NAME-HERE":
                    password: "PASSWORD-HERE"
            dhcp4: true
```

4. Apply the configuration.

```shell
sudo netplan apply
```

5. Give it a second and then check if the network is up.

```shell
ip a
```

## Camera setup

> Use raspberry pi os

### Pi Configuration

In the new Raspberry Pi OS, the camera is disabled by default. To run the following command to enable the camera.

```shell
sudo raspi-config
```

- Select `Interfacing Options`
  - `Legacy Camera` and then `Yes` to enable the camera.
  - `I2C` and then `Yes` to enable the I2C interface.
  - `SSH` and then `Yes` to enable the SSH interface.
- Select `Performance Options`
  - `GPU Memory` and then `128` to set the GPU memory to 128MB. 
### RTSP protocol

<details>

> Use [`rtsp-simple-server`](https://github.com/aler9/rtsp-simple-server#publish-to-the-server) and `ffmpeg`

1. Update configuration file for stream.

```shell
sudo nano /boot/firmware/config.txt
```

Add the following lines to the end of the file

```text
# Enable camera
start_X=1
# Change gpu memory to 128M
gpu_mem=128
```

2. Download `rtsp-simple-server`

Find the architecture of the system

```shell
$ uname -m
armv7l
```

Download executable from [`rtsp-simple-server`](https://github.com/aler9/rtsp-simple-server/releases/tag/v0.18.4). Make sure the architecture match.

```shell
wget https://github.com/aler9/rtsp-simple-server/releases/download/v0.18.4/rtsp-simple-server_v0.18.4_linux_armv7.tar.gz

```

3. Unzip tar file.

```shell
tar -xvf rtsp-simple-server_v0.18.4_linux_armv7.tar.gz
```

4. Modify the `rtsp-simple-server.yml`. Replace the `path` section with the following

```text
paths:
  cam:
    runOnInit: ffmpeg -f v4l2 -framerate 15 -fflags nobuffer  -i /dev/video0 -pix_fmt yuv420p -preset ultrafast -b:v 600k -f rtsp rtsp://localhost:$RTSP_PORT/$RTSP_PATH
    runOnInitRestart: yes
```

5. Run the server.

```shell
./rtsp-simple-server
```

6. Use any stream player to view the stream.

```
rtsp://<ip>:8554/cam
```

</details>

### WebRTC

### MJPEG

> Use [`mjpg-streamer`](https://github.com/jacksonliam/mjpg-streamer)

1. clone the repository

```shell
git clone https://github.com/jacksonliam/mjpg-streamer.git
```

2. Unzip the repository

```shell
tar -xf mjpg-streamer.tar.gz
```

3. install required packages

```shell
sudo apt-get install cmake libjpeg8-dev gcc g++
```

4. Compile and install the program

```shell
cd mjpg-streamer-experimental
make
sudo make install
```

5. Start the server. Video output `1280x720`

```shell
export LD_LIBRARY_PATH=.
./mjpg_streamer -o "output_http.so -w ./www -p 8080" -i "input_uvc.so -r 1280x720"
```

## Add to startup

> Added to start up by adding the a new service to the `systemd`

> Assume the `mjpg-server` is installed in `/opt/mjpg-streamer`

1. Create a new execute script to start the server.

```shell
nano /opt/mjpg-streamer/start.sh
```

2. Add the following lines to the script.

```bash
#!/bin/bash

cd /opt/mjpg-streamer
export LD_LIBRARY_PATH=.
./mjpg_streamer -o "output_http.so -w ./www -p 8080" -i "input_uvc.so -r 1280x720"
```

3. Set the permission of the script.

```shell
sudo chmod +x /opt/mjpg-streamer/start.sh
```

4. Create a new service file.

```shell
sudo nano /lib/systemd/system/mjpg-streamer.service
```

5. Add the following lines to the file.

```text
[Unit]
Description=Start mjpg-streamer at boot time

[Service]
ExecStart=/opt/mjpg-streamer/start.sh

[Install]
WantedBy=multi-user.target
```

6. Enable the service.

```shell
sudo systemctl enable mjpg-streamer.service
```

7. Start the service.

```shell
sudo systemctl start mjpg-streamer.service
```

8. Check the status of the service.

```shell
sudo systemctl status mjpg-streamer.service
```

## Install battery monitor service

1. Install the required packages from `requirements.txt`

```shell
sudo pip3 install -r requirements.txt
```

2. copy the `voltage_monitor.py` to home directory.
3. Create a new bash file `voltage_monitor.sh` in home directory.

```bash
#!/bin/bash
python3 /home/pi/voltage_monitor.py
```
4. Add execute permission to the file
```shell
sudo chmod +x /home/pi/voltage_monitor.sh
```
5. Create a new service file.
```shell
sudo nano /lib/systemd/system/voltage_monitor.service
```
6. Add the following lines to the file.
```text
[Unit]
Description=Start voltage monitor at boot time

[Service]
ExecStart=/home/pi/voltage_monitor.sh

[Install]
WantedBy=multi-user.target
```
6. Enable the service.

```shell
sudo systemctl enable voltage_monitor.service
```

7. Start the service.

```shell
sudo systemctl start voltage_monitor.service
```

8. Check the status of the service.

```shell
sudo systemctl status voltage_monitor.service
```
