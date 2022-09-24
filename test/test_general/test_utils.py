from general.utils import Position

from unittest import TestCase

import pytest


class TestPosition():
    def test_add_position(self):
        p1 = Position(0,0,0)
        p2 = Position(1,1,1)
        assert p1 + p2 == Position(1,1,1)
    
    def test_add_int(self):
        p1 = Position(0,0,0)
        assert p1 + 1 == Position(1,1,1)

    def test_sub_position(self):
        p1 = Position(0,0,0)
        p2 = Position(1,1,1)
        assert p1 - p2 == Position(-1,-1,-1)
    
    def test_sub_int(self):
        p1 = Position(0,0,0)
        assert p1 - 1 == Position(-1,-1,-1)
        
    def test_distance(self):
        p1 = Position(0,0,0)
        p2 = Position(1,1,1)
        assert p1.distance(p2) == 3 ** 0.5