text = \
"""
[drone]

[drone.drone1]
name = "drone1"
uri = "radio://0/80/2M/E7E7E7E702"
stream = "192.168.0.1"

[drone.drone2]
name = "drone2"
uri = "radio://0/80/2M/E7E7E7E703"
stream = "192.168.0.1"
"""

import os 
dir_path = os.path.dirname(os.path.realpath(__file__))

from os import listdir
from os.path import isfile, join

config_path = dir_path + "/configs"
config_files = [f for f in listdir(config_path) if isfile(join(config_path, f))]

for config in config_files:
    with open(config_path + "/" + config, "a") as f:
        print(text, file=f)