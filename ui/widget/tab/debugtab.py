from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QGridLayout,
                             QHBoxLayout, QLabel, QPushButton, QRadioButton)

import setting
from general.utils import AxisDirection
from hub.drone import Drone, FlyControlMode, FlyMode, Motion, Position, DronePowerAction
from log.logger import LOGGER
from ui.widget.dialog.locationeditdialog import LocationEditDialog
from ui.widget.tab.tab import Tab
from map.path import PathList, Path


class DebugTabSignal(QObject):
    fly_mode = pyqtSignal(FlyMode)
    control_mode = pyqtSignal(FlyControlMode)
    manually_control_hold = pyqtSignal(bool)
    auto_avoid_obstacle = pyqtSignal(bool)
    fly_motion = pyqtSignal(Motion)
    hover_position = pyqtSignal(object)


class DebugTab(Tab):
    def __init__(self, drone: Drone, parent=None):
        super().__init__(drone.name, parent)
        self._drone = drone
        self._setting = drone.fly_control.setting
        self.signals = DebugTabSignal()
        self._setup_ui()
        self._add_callbacks()
        self._connect_signal()

    def _setup_ui(self):
        main_layout = QGridLayout(self)
        self.setLayout(main_layout)
        row = 0

        # Fly Mode
        main_layout.addWidget(QLabel("Fly Mode"), row, 0)
        self.fly_mode_list = QComboBox(self)
        for mode in FlyMode:
            self.fly_mode_list.addItem(mode.name)
        mode = self._setting.fly_mode.get().name
        index = 0 if self.fly_mode_list.findText(
            mode) == -1 else self.fly_mode_list.findText(mode)
        self.fly_mode_list.setCurrentIndex(index)
        self.fly_mode_list.currentTextChanged.connect(self._fly_mode_changed)
        main_layout.addWidget(self.fly_mode_list, row, 1)
        row += 1

        # Control Mode
        main_layout.addWidget(QLabel("Control Mode"), row, 0)
        control_mode_group = QButtonGroup()
        cm_layout = QHBoxLayout()
        main_layout.addLayout(cm_layout, row, 1)

        self.rb_auto = QRadioButton("Auto")
        cm_layout.addWidget(self.rb_auto)
        control_mode_group.addButton(self.rb_auto, 1)

        self.rb_manual = QRadioButton("Manual")
        cm_layout.addWidget(self.rb_manual)
        control_mode_group.addButton(self.rb_manual, 2)

        if self._setting.control_mode.get() == FlyControlMode.AUTO:
            self.rb_auto.setChecked(True)
        else:
            self.rb_manual.setChecked(True)
        self.rb_manual.pressed.connect(
            lambda: self._control_mode_changed(FlyControlMode.MANUALLY))
        self.rb_auto.pressed.connect(
            lambda: self._control_mode_changed(FlyControlMode.AUTO))

        row += 1

        # Manual Control Hold Enable
        main_layout.addWidget(QLabel("Manual Hold"), row, 0)
        self.cb_manual_hold = QCheckBox()
        self.cb_manual_hold.setChecked(
            self._setting.manually_control_hold.get())
        self.cb_manual_hold.stateChanged.connect(self._manual_hold_changed)

        main_layout.addWidget(self.cb_manual_hold, row, 1)
        row += 1

        # Auto Avoid Enable
        main_layout.addWidget(QLabel("Auto Avoid"), row, 0)
        self.cb_auto_avoid = QCheckBox()
        self.cb_auto_avoid.setChecked(self._setting.auto_avoid_obstacle.get())
        self.cb_auto_avoid.stateChanged.connect(self._auto_avoid_changed)

        main_layout.addWidget(self.cb_auto_avoid, row, 1)
        row += 1

        # Reset
        main_layout.addWidget(QLabel("Reset"), row, 0)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setToolTip("Reset all settings to default")
        self.btn_reset.clicked.connect(self._reset_on_click)

        main_layout.addWidget(self.btn_reset, row, 1)
        row += 1

        # Fly Command
        main_layout.addWidget(QLabel("Fly Command"), row, 0)

        self.lb_fly_command = QLabel(str(self._setting.fly_motion.get()))
        main_layout.addWidget(self.lb_fly_command, row, 1)
        row += 1

        main_layout.addWidget(QLabel("Hover Position"), row, 0)
        layout = QHBoxLayout()
        self.lb_hover_position = QLabel(str(self._setting.hover_position.get(
        ) if self._setting.hover_position.get() else "None"))
        self.btn_set_hover_position = QPushButton("Set")
        self.btn_set_hover_position.clicked.connect(
            self._set_hover_position_on_click)
        layout.addWidget(self.lb_hover_position)
        layout.addWidget(self.btn_set_hover_position)
        main_layout.addLayout(layout, row, 1)
        row += 1

        main_layout.addWidget(QLabel("Axis Alignment"), row, 0)
        align_layout = QHBoxLayout()
        main_layout.addLayout(align_layout, row, 1)

        self.btn_align_x_pos = QPushButton("X+")
        self.btn_align_x_pos.clicked.connect(
            lambda: self._align_on_click(AxisDirection.x_positive()))
        self.btn_align_x_pos.setMaximumWidth(30)
        align_layout.addWidget(self.btn_align_x_pos)

        self.btn_align_x_neg = QPushButton("X-")
        self.btn_align_x_neg.clicked.connect(
            lambda: self._align_on_click(AxisDirection.x_negative()))
        self.btn_align_x_neg.setMaximumWidth(30)
        align_layout.addWidget(self.btn_align_x_neg)

        self.btn_align_y_pos = QPushButton("Y+")
        self.btn_align_y_pos.clicked.connect(
            lambda: self._align_on_click(AxisDirection.y_positive()))
        self.btn_align_y_pos.setMaximumWidth(30)
        align_layout.addWidget(self.btn_align_y_pos)

        self.btn_align_y_neg = QPushButton("Y-")
        self.btn_align_y_neg.clicked.connect(
            lambda: self._align_on_click(AxisDirection.y_negative()))
        self.btn_align_y_neg.setMaximumWidth(30)
        align_layout.addWidget(self.btn_align_y_neg)

        row += 1

        main_layout.addWidget(QLabel("Start Path"), row, 0)
        self.btn_start_path = QPushButton("Start")
        self.btn_start_path.clicked.connect(self._fly_path_on_click)
        main_layout.addWidget(self.btn_start_path, row, 1)

        row += 1

        main_layout.addWidget(QLabel("Power Switch"), row, 0)
        layout = QHBoxLayout()
        self.btn_power_off = QPushButton("Off")
        self.btn_power_off.clicked.connect(
            lambda: self._power_action_on_click(DronePowerAction.POWER_OFF))
        layout.addWidget(self.btn_power_off)
        self.btn_reboot = QPushButton("Reboot")
        self.btn_reboot.clicked.connect(
            lambda: self._power_action_on_click(DronePowerAction.REBOOT))
        layout.addWidget(self.btn_reboot)
        main_layout.addLayout(layout, row, 1)
        row += 1

        main_layout.addWidget(QLabel("Path Test"), row, 0)
        self.btn_path_test = QPushButton("Go To Path1")
        self.btn_path_test.clicked.connect(self._path_test_on_click)
        main_layout.addWidget(self.btn_path_test, row, 1)
        row += 1

    def _add_callbacks(self):
        self._setting.fly_mode.callbacks.add_callback(
            self.signals.fly_mode.emit)
        self._setting.control_mode.callbacks.add_callback(
            self.signals.control_mode.emit)
        self._setting.manually_control_hold.callbacks.add_callback(
            self.signals.manually_control_hold.emit)
        self._setting.auto_avoid_obstacle.callbacks.add_callback(
            self.signals.auto_avoid_obstacle.emit)
        self._setting.fly_motion.callbacks.add_callback(
            self.signals.fly_motion.emit)
        self._setting.hover_position.callbacks.add_callback(
            self.signals.hover_position.emit)

    def _connect_signal(self):
        self.signals.fly_mode.connect(self._fly_mode_ui_listener)
        self.signals.control_mode.connect(self._control_mode_ui_listener)
        self.signals.manually_control_hold.connect(
            self._manual_hold_ui_listener)
        self.signals.auto_avoid_obstacle.connect(
            self._auto_avoid_obstacle_ui_listener)
        self.signals.fly_motion.connect(self._fly_motion_ui_listener)
        self.signals.hover_position.connect(self._hover_position_ui_listener)

    @pyqtSlot(FlyMode)
    def _fly_mode_ui_listener(self, mode: FlyMode):
        if self.fly_mode_list.currentText().upper() == mode.name.upper():
            return

        index = self.fly_mode_list.findText(mode.name)
        self.fly_mode_list.setCurrentIndex(index)

    @pyqtSlot(bool)
    def _manual_hold_ui_listener(self, checked):
        if self.cb_manual_hold.isChecked() == checked:
            return

        self.cb_manual_hold.setChecked(checked)

    @pyqtSlot(FlyControlMode)
    def _control_mode_ui_listener(self, mode: FlyControlMode):

        if self.rb_auto.isChecked() and mode == FlyControlMode.AUTO:
            return
        if self.rb_manual.isChecked() and mode == FlyControlMode.MANUALLY:
            return
        if mode == FlyControlMode.AUTO:
            self.rb_auto.setChecked(True)
        else:
            self.rb_manual.setChecked(True)

    @pyqtSlot(bool)
    def _auto_avoid_obstacle_ui_listener(self, checked):
        if self.cb_auto_avoid.isChecked() == checked:
            return
        self.cb_auto_avoid.setChecked(checked)

    @pyqtSlot(Motion)
    def _fly_motion_ui_listener(self, motion: Motion):
        self.lb_fly_command.setText(str(motion))

    @pyqtSlot(object)
    def _hover_position_ui_listener(self, position: Position | None):
        if position is None:
            self.lb_hover_position.setText("None")
        else:
            self.lb_hover_position.setText(str(position))

    def _fly_mode_changed(self, text: str):
        if self._setting.fly_mode.get().name == text:
            return  # no change
        self._setting.fly_mode.set(FlyMode.get_by_name(text))

    def _control_mode_changed(self, mode: FlyControlMode):
        self._setting.control_mode.set(mode)

    def _manual_hold_changed(self, checked):
        checked = self.cb_manual_hold.isChecked()
        if self._setting.manually_control_hold.get() == checked:
            return
        self._setting.manually_control_hold.set(checked)

    def _auto_avoid_changed(self, checked):
        checked = self.cb_auto_avoid.isChecked()
        if self._setting.auto_avoid_obstacle.get() == checked:
            return
        self._setting.auto_avoid_obstacle.set(checked)

    def _reset_on_click(self):
        self._setting.reset()

    def _align_on_click(self, axis: AxisDirection):
        if self._drone.is_flying:
            self._drone.fly_control.debug_add_command(axis)

    def _fly_path_on_click(self):
        path = Path()
        path.add_position(Position(1, 0, 0.4))
        path.add_position(Position(1, -1, 0.4))
        path.add_position(Position(0, -1, 0.4))
        path.add_position(Position(0, 0, 0.4))
        print("pressed")
        self._drone.fly_control.debug_add_command(path)

    def _power_action_on_click(self, state: DronePowerAction):
        self._drone.perform_power_action(state)

    def _set_hover_position_on_click(self):
        dialog = LocationEditDialog(show_name=False, mode=LocationEditDialog.Mode.ADD)
        if dialog.exec():
            self._setting.hover_position.set(dialog.location.position)

    def _path_test_on_click(self):
        try:
            with open(setting.PATH_PATH, 'r') as f:
                paths = PathList.load(f)
                self._drone.fly_control.go_to(paths[0])

        except IOError:
            LOGGER.error("Cannot load path file")
        except Exception as e:
            LOGGER.error("Cannot load path file: " + str(e))
