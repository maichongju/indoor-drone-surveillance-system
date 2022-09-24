from enum import Enum


class DroneModel(Enum):
    BOLT = 0,
    CRAZYFILE = 1,

class Firmware:

    CRAZYFILE = [
        "8c606d1f8f89" # 2022.05
    ]
    
    BOLT = [
        "c6269c10c3ab", # 2022.05
        "17330d2a7234"
    ]
    
    @staticmethod
    def get_model(revision:str) -> DroneModel:
        """ Try to get the drone model from the revision string 
        """
        if revision in Firmware.CRAZYFILE:
            return DroneModel.CRAZYFILE
        elif revision in Firmware.BOLT:
            return DroneModel.BOLT
        
        return DroneModel.CRAZYFILE
