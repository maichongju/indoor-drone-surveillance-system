import pytest

from hub.drone import Motion
from general.utils import Position


class TestDroneMovement:
    def test_add(self):
        m = Motion(1, 1, 1, 1)
        p = Position(1, 1, 1)

        # DroneMovement + DroneMovement
        assert m + m == Motion(2, 2, 2,
                               2), "DroneMovement + DroneMovement Failed"

        assert m + p == Motion(2, 2, 2, 1), "DroneMovement + Position Failed"

    def test_sub(self):
        m = Motion(1, 1, 1, 1)
        p = Position(1, 1, 1)

        # DroneMovement + DroneMovement
        assert m - m == Motion(0, 0, 0,
                               0), "DroneMovement - DroneMovement Failed"

        assert m - p == Motion(0, 0, 0, 1), "DroneMovement - Position Failed"
