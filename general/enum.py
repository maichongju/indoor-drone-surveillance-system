from enum import Enum as pEnum
from enum import IntEnum as pIntEnum
from enum import auto


class Enum(pEnum):

    def __getstate__(self):
        return self.name
    
    def __str__(self):
        return self.name

class IntEnum(pIntEnum):
    def __getstate__(self):
        return self.name
    
    def __str__(self):
        return self.name