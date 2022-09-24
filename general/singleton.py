"""
File Contain global singleton objects
"""

from dataclasses import dataclass
from config import Config
from hub.location import Locations

@dataclass
class Singleton:
    Config: Config
    Locations: Locations
    def __init__(self):
        self.Config : Config = Config()
        self.Locations: Locations = Locations()
        
SINGLETON = Singleton()
        
