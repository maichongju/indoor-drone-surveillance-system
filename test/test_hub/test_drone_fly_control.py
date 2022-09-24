import pytest
from hub.drone import FlyControlThread, Drone
from general.utils import Axis, Position


class TestDroneFlyControlYawAxis:

    margin = 5
    max_yaw = 360/10

    @pytest.fixture
    def flyControl(self):
        drone = Drone('', '', '')
        flyControl = FlyControlThread(drone)
        return flyControl

    @pytest.mark.parametrize("axis, dist, current_yaw, expected",
                             [
                                 (Axis.X, Position(-5, 0, 0), 45.0, max_yaw),
                                 (Axis.X, Position(-5, 0, 0), -45.0, -max_yaw),
                                 (Axis.X, Position(-5, 0, 0), 15.0, 15),
                                 (Axis.X, Position(-5, 0, 0), -15.0, -15),
                                 (Axis.X, Position(-5, 0, 0), -135.0, -max_yaw),
                                 (Axis.X, Position(-5, 0, 0), 135.0, max_yaw),
                                 (Axis.X, Position(-5, 0, 0), 4.0, 0),
                                 (Axis.X, Position(-5, 0, 0), -4.0, 0),
                             ])
    def test_yaw_axis_x_positive(self,
                                 flyControl: FlyControlThread,
                                 axis, dist, current_yaw, expected):
        assert flyControl._get_yaw(
            axis, dist, current_yaw, self.margin, self.max_yaw) == expected

    @pytest.mark.parametrize("axis, dist, current_yaw, expected",
                             [
                                 (Axis.X, Position(5, 0, 0), 45.0, -max_yaw),
                                 (Axis.X, Position(5, 0, 0), -45.0, max_yaw),
                                 (Axis.X, Position(5, 0, 0), -170.0, 10),
                                 (Axis.X, Position(5, 0, 0), 170.0, -10),
                                 (Axis.X, Position(5, 0, 0), -135.0, max_yaw),
                                 (Axis.X, Position(5, 0, 0), 135.0, -max_yaw),
                                 (Axis.X, Position(5, 0, 0), 176.0, 0),
                                 (Axis.X, Position(5, 0, 0), -176.0, 0),
                             ])
    def test_yaw_axis_x_negative(self,
                                 flyControl: FlyControlThread,
                                 axis, dist, current_yaw, expected):
        assert flyControl._get_yaw(
            axis, dist, current_yaw, self.margin, self.max_yaw) == expected

    @pytest.mark.parametrize("axis, dist, current_yaw, expected",
                             [
                                 (Axis.Y, Position(0, -5, 0), 45.0, -max_yaw),
                                 (Axis.Y, Position(0, -5, 0), -45.0, -max_yaw),
                                 (Axis.Y, Position(0, -5, 0), 80, -10),
                                 (Axis.Y, Position(0, -5, 0), 100, 10),
                                 (Axis.Y, Position(0, -5, 0), -135.0, max_yaw),
                                 (Axis.Y, Position(0, -5, 0), 135.0, max_yaw),
                                 (Axis.Y, Position(0, -5, 0), 86.0, 0),
                                 (Axis.Y, Position(0, -5, 0), 94.0, 0),
                             ])
    def test_yaw_axis_y_negative(self,
                                 flyControl: FlyControlThread,
                                 axis, dist, current_yaw, expected):
        assert flyControl._get_yaw(
            axis, dist, current_yaw, self.margin, self.max_yaw) == expected
        
    @pytest.mark.parametrize("axis, dist, current_yaw, expected",
                             [
                                 (Axis.Y, Position(0, 5, 0), 45.0, max_yaw),
                                 (Axis.Y, Position(0, 5, 0), -45.0, max_yaw),
                                 (Axis.Y, Position(0, 5, 0), -80, 10),
                                 (Axis.Y, Position(0, 5, 0), -100, -10),
                                 (Axis.Y, Position(0, 5, 0), -135.0, -max_yaw),
                                 (Axis.Y, Position(0, 5, 0), 135.0, -max_yaw),
                                 (Axis.Y, Position(0, 5, 0), -86.0, 0),
                                 (Axis.Y, Position(0, 5, 0), -94.0, 0),
                             ])
    def test_yaw_axis_y_positive(self,
                                 flyControl: FlyControlThread,
                                 axis, dist, current_yaw, expected):
        assert flyControl._get_yaw(
            axis, dist, current_yaw, self.margin, self.max_yaw) == expected
