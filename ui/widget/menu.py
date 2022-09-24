import logging

from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtGui import QActionGroup

from hub.drone import Drone
from hub.drone import FlyMode

from log.logger import LOGGER

class TestDroneMenu(QMenu):
    def __init__(self, drone: Drone, parent=None):
        super().__init__(parent)
        self.setTitle(drone.name)
        self._drone = drone
        self._mode_sub_menu()
        self._pos_sub_menu()

    def _mode_sub_menu(self):

        mode_sub_menu = QMenu('Mode', self)
        self.addMenu(mode_sub_menu)

        mode_action_group = QActionGroup(mode_sub_menu)

        mode_normal_action = QAction('Normal', mode_sub_menu)
        mode_hover_action = QAction('Hover', mode_sub_menu)

        mode_action_group.addAction(mode_normal_action)
        mode_action_group.addAction(mode_hover_action)

        mode_normal_action.setCheckable(True)
        mode_hover_action.setCheckable(True)

        mode_sub_menu.addAction(mode_normal_action)
        mode_sub_menu.addAction(mode_hover_action)

        # Default mode is normal
        mode_normal_action.setChecked(True)

        # mode_normal_action.triggered.connect(
        #     lambda: self._drone.fly_control.set_fly_mode(FlyMode.NORMAL))
        # mode_hover_action.triggered.connect(
        #     lambda: self._drone.fly_control.set_fly_mode(FlyMode.HOVER))

    def _pos_sub_menu(self):
        pos_sub_menu = QMenu('Position', self)
        self.addMenu(pos_sub_menu)
        
        reset_pos_action = QAction('Reset', pos_sub_menu)
        reset_pos_action.setToolTip('Reset Drone position. Will take 2 seconds.')
        # reset_pos_action.triggered.connect(self._drone.fly_control._reset_position_estimator())
        pos_sub_menu.addAction(reset_pos_action)
        

        
        