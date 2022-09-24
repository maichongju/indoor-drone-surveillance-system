from copy import deepcopy
from hub.location import Locations
from general.utils import Position
import pytest


PATH = 'test/test_hub/locations/'

def get_path(file_name):
    return PATH + file_name

class TestLocations():
    
    def test_normal(self):
        location = Locations()
        location.load(get_path('locations.json'))
        assert len(location.locations) == 2
        assert location.locations[0].name == 'Front Door'
        assert location.locations[0].position == Position(0,0,0)
        assert location.locations[1].name == 'Back Door'
        assert location.locations[1].position == Position(1,1,1)
    
    def test_not_list(self):
        location = Locations()
        location.load(get_path('not_list.json'))
        assert len(location.locations) == 0
        
    def test_missing_name(self):
        location = Locations()
        location.load(get_path('missing_name.json'))
        assert len(location.locations) == 1
        
    def test_position_invalid(self):
        location = Locations()
        location.load(get_path('position_invalid.json'))
        assert len(location.locations) == 1
        
    def test_position_missing_x(self):
        location = Locations()
        location.load(get_path('position_missing_x.json'))
        assert len(location.locations) == 1
        
    def test_position_x_invalid(self):
        location = Locations()
        location.load(get_path('position_x_invalid.json'))
        assert len(location.locations) == 1
        
    def test_deepcopy(self):
        location = Locations()
        location.load(get_path('locations.json'))
        location_ = deepcopy(location)
        location._locations[0].name = 'Changed'
        assert location_._locations[0].name == 'Front Door'
        
    