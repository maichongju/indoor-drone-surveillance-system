import sys
from enum import Enum
from threading import Thread

from general.utils import Position
from hub.drone import Drone, DroneException, FlyCommandManually, FlyStatus
from log import DroneInfo, get_battery_state_name, get_loco_mode_name
from log.logger import LOGGER
from PyQt6.QtCore import (QObject, QRunnable, Qt, QThreadPool, pyqtSignal,
                          pyqtSlot)
from PyQt6.QtWidgets import (QCheckBox, QDialog, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QMessageBox, QProgressBar,
                             QPushButton, QVBoxLayout, QWidget)
from ui.icon import Icon
from ui.widget.dialog import GoToDialog
from ui.widget.tab.tab import Tab
from ui.widget.utils import (StylePreset, set_label_style,
                             set_label_style_threshold)
from ui.widget.widget import DroneStreamWidget, IconLabel, ThrustBar

# for when to display the text to red bold
CRITICAL_THRESHOLD = {
    # in m
    "front_distance": 0.2,
    "back_distance": 0.2,
    "left_distance": 0.2,
    "right_distance": 0.2,
    "battery_level": 20,
    "voltage_level": 6.6
}

PROGRESSBAR_STYLE = """
QProgressBar {
    border: 1px solid grey;
    text-align: center;
}
"""

PROGRESSBAR_BATTERY = """
QProgressBar {
    border: 1px solid grey;
    text-align: center;
}

QProgressBar::chunk {
    background-color: %s;
    width: 9px;
    margin: 0.5px;
}
"""


PROGRESSBAR_GOOD_COLOR = "#6afb6a"
PROGRESSBAR_MEDIUM_COLOR = "#fbd76a"
PROGRESSBAR_BAD_COLOR = "#fb6a6a"

LABEL_HEIGHT = 'Height:'
LABEL_BATTERY = 'Battery:'
LABEL_FRONT_DISTANCE = 'Front:'
LABEL_BACK_DISTANCE = 'Back:'
LABEL_LEFT_DISTANCE = 'Left:'
LABEL_RIGHT_DISTANCE = 'Right:'
LABEL_PITCH = 'Pitch:'
LABEL_ROLL = 'Roll:'
LABEL_YAW = 'Yaw:'
LABEL_POS_X = 'X:'
LABEL_POS_Y = 'Y:'
LABEL_POS_Z = 'Z:'


class _Icon(Enum):
    CONNECTED = Icon.GREEN_DOT
    DISCONNECTED = Icon.RED_DOT
    CONNECTING = Icon.YELLOW_DOT
    DISCONNECTING = Icon.YELLOW_DOT
    LANDING = Icon.PLANE_LANDING
    LANDED = Icon.HOME
    TAKING_OFF = Icon.PLANE_TAKING_OFF
    FLYING = Icon.PLANE
    GO_TO = Icon.DESTINATION
    STOP = Icon.STOP_SIGN


class DroneSignals(QObject):
    """Signal class for the drone widget
    """
    # Signal for ui core update
    ui_core_update = pyqtSignal(DroneInfo)

    # Signal for ui multi ranger update
    ui_multi_ranger_update = pyqtSignal(DroneInfo)

    # Singal for ui motor/thrust update
    ui_motor_thrust_update = pyqtSignal(DroneInfo)

    # Signal for landing and taking off
    ui_drone_status_update = pyqtSignal(FlyStatus)

    # Signal for position update
    ui_position_update = pyqtSignal(DroneInfo)

    # Signal for battery update
    ui_battery_update = pyqtSignal(DroneInfo)

    # Signal for loco update
    ui_loco_update = pyqtSignal(DroneInfo)

    # Signal for link quality update
    link_quality_update = pyqtSignal(float)

    # Signal for drone disconnected
    disconnected = pyqtSignal()

    # Signal for the connection status
    connection_lost = pyqtSignal(str, str)


class DroneWidget(Tab):
    def __init__(self, drone: Drone, parent=None):
        super().__init__(name=drone.name, parent=parent)
        self._drone = drone
        self.signals = DroneSignals()
        self._thread_pool = QThreadPool()
        self._setup_ui()
        self._btn_reset()
        self._setup_drone_callbacks()
        self._setup_drone_ui_callbacks()
        self._setup_signals()
        self._crash_warning_shown = False

    def _setup_drone_callbacks(self):
        """Helper function to set up crazyflie callbacks
        """
        # Connection lost callback
        self._drone._scf.cf.connection_lost.add_callback(
            self.signals.connection_lost.emit)
        self._drone._scf.cf.link_quality_updated.add_callback(
            self.signals.link_quality_update.emit)

    def _setup_signals(self):
        """Connect all the call backs function to the GUI
        """
        self.signals.connection_lost.connect(self._connection_lost)
        self.signals.link_quality_update.connect(self._ui_link_quality_update)
        self.signals.ui_core_update.connect(self._ui_core_callback)
        self.signals.ui_multi_ranger_update.connect(
            self._ui_multi_ranger_callback)
        self.signals.ui_motor_thrust_update.connect(
            self._ui_motor_thrust_callback)
        self.signals.ui_drone_status_update.connect(
            self._ui_drone_status_callback)
        self.signals.ui_position_update.connect(self._ui_position_callback)
        self.signals.ui_battery_update.connect(self._ui_battery_callback)
        self.signals.ui_loco_update.connect(self._ui_loco_callback)

    def _setup_drone_ui_callbacks(self):
        """Helper function to set up all the drone callback
        """
        # self._drone.drone_callbacks.connection_lost = self._cb_drone_connection_lost
        self._drone.drone_callbacks.core_logger_callback.add_callback(
            self.signals.ui_core_update.emit)
        self._drone.drone_callbacks.multi_ranger_logger_callback.add_callback(
            self.signals.ui_multi_ranger_update.emit)
        self._drone.drone_callbacks.motor_thrust_logger_callback.add_callback(
            self.signals.ui_motor_thrust_update.emit)
        self._drone.drone_callbacks.drone_status_callback.add_callback(
            self.signals.ui_drone_status_update.emit)
        self._drone.drone_callbacks.position_logger_callback.add_callback(
            self.signals.ui_position_update.emit)
        self._drone.drone_callbacks.battery_logger_callback.add_callback(
            self.signals.ui_battery_update.emit)
        self._drone.drone_callbacks.loco_logger_callback.add_callback(
            self.signals.ui_loco_update.emit)

    def _setup_ui(self):

        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        self.left_layout = QVBoxLayout()

        self._setup_top_labels()

        self._setup_status_group()

        self._setup_btn_layout()

        self.stream_widget = VideoStream(self._drone)
        main_layout.addLayout(self.left_layout)
        main_layout.addWidget(self.stream_widget)

    def _setup_top_labels(self):

        layout = QVBoxLayout()

        self.lbl_drone_name = QLabel(self._drone.name)
        self.lbl_drone_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_drone_name)

        self.lbl_drone_uri = QLabel(self._drone.uri)
        self.lbl_drone_uri.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_drone_uri)

        drone_status_layout = QHBoxLayout()
        # Drone Connection Status
        self.lbl_connection_status = IconLabel(
            "Disconnected", qicon=_Icon.DISCONNECTED.value)
        drone_status_layout.addWidget(self.lbl_connection_status)

        self.lbl_drone_status = IconLabel(
            "Landed", qicon=_Icon.LANDED.value)
        drone_status_layout.addWidget(self.lbl_drone_status)

        layout.addLayout(drone_status_layout)
        self._setup_deck_status(layout)

        self.left_layout.addLayout(layout)

    def _setup_deck_status(self, layout: QWidget):
        self.layout_deck_status = QHBoxLayout()
        layout.addLayout(self.layout_deck_status)

        self.lbl_deck_z_flow_status = IconLabel(
            "Z-Flow", qicon=_Icon.DISCONNECTED.value)
        self.lbl_deck_z_flow_status.setToolTip(
            "Z-Flow Deck")
        self.layout_deck_status.addWidget(self.lbl_deck_z_flow_status)

        self.lbl_deck_loco_status = IconLabel(
            "Loco", qicon=_Icon.DISCONNECTED.value)
        self.lbl_deck_loco_status.setToolTip(
            "Loco Positioning")
        self.layout_deck_status.addWidget(self.lbl_deck_loco_status)

        self.lbl_deck_multi_ranger_status = IconLabel(
            "Ranger", qicon=_Icon.DISCONNECTED.value)
        self.lbl_deck_multi_ranger_status.setToolTip(
            "Multi-Ranger")
        self.layout_deck_status.addWidget(
            self.lbl_deck_multi_ranger_status)

    def _setup_status_group(self):
        self.gb_status = QGroupBox("Status")
        main_layout = QVBoxLayout()
        self.gb_status.setLayout(main_layout)

        # Link Quality
        quality_layout = QHBoxLayout()
        main_layout.addLayout(quality_layout)

        self.lbl_link_quality = QLabel("Signal")
        self.lbl_link_quality.setMinimumWidth(50)
        quality_layout.addWidget(self.lbl_link_quality)
        self.pb_link_quality = QProgressBar()
        self.pb_link_quality.setMaximum(100)
        self.pb_link_quality.setMinimum(0)
        self.pb_link_quality.setValue(0)
        self.pb_link_quality.setMaximumHeight(15)
        self.pb_link_quality.setStyleSheet(PROGRESSBAR_STYLE)
        quality_layout.addWidget(self.pb_link_quality)

        # Battery
        battery_layout = QHBoxLayout()
        main_layout.addLayout(battery_layout)

        self.lbl_battery_level = QLabel("Battery")
        self.lbl_battery_level.setMinimumWidth(50)
        battery_layout.addWidget(self.lbl_battery_level)
        self.pb_battery_level = QProgressBar()
        self.pb_battery_level.setMaximum(100)
        self.pb_battery_level.setMinimum(0)
        self.pb_battery_level.setValue(0)
        self.pb_battery_level.setMaximumHeight(15)
        self.pb_battery_level.setStyleSheet(PROGRESSBAR_STYLE)
        battery_layout.addWidget(self.pb_battery_level)

        self.lbl_battery_voltage = QLabel("0.000 V")
        battery_layout.addWidget(self.lbl_battery_voltage)

        # Core / Multi-Ranger Status
        status_layout = QGridLayout()
        main_layout.addLayout(status_layout)

        self.lbl_height = QLabel(f"{LABEL_HEIGHT} N/A")
        status_layout.addWidget(self.lbl_height, 1, 1)

        self.lbl_battery_status = QLabel("")
        status_layout.addWidget(self.lbl_battery_status, 1, 2)

        self.lbl_front_distance = QLabel(f"{LABEL_FRONT_DISTANCE} N/A")
        status_layout.addWidget(self.lbl_front_distance, 2, 1)

        self.lbl_back_distance = QLabel(f"{LABEL_BACK_DISTANCE} N/A")
        status_layout.addWidget(self.lbl_back_distance, 2, 2)

        self.lbl_left_distance = QLabel(f"{LABEL_LEFT_DISTANCE} N/A")
        status_layout.addWidget(self.lbl_left_distance, 3, 1)

        self.lbl_right_distance = QLabel(f"{LABEL_RIGHT_DISTANCE} N/A")
        status_layout.addWidget(self.lbl_right_distance, 3, 2)

        self.lbl_pitch = QLabel(f"{LABEL_PITCH} N/A")
        status_layout.addWidget(self.lbl_pitch, 4, 1)

        self.lbl_roll = QLabel(f"{LABEL_ROLL} N/A")
        status_layout.addWidget(self.lbl_roll, 4, 2)

        self.lbl_yaw = QLabel(f"{LABEL_YAW} N/A")
        status_layout.addWidget(self.lbl_yaw, 5, 1)

        self.lbl_pos_x = QLabel(f"{LABEL_POS_X} N/A")
        status_layout.addWidget(self.lbl_pos_x, 5, 2)

        self.lbl_pos_y = QLabel(f"{LABEL_POS_Y} N/A")
        status_layout.addWidget(self.lbl_pos_y, 6, 1)

        self.lbl_pos_z = QLabel(f"{LABEL_POS_Z} N/A")
        status_layout.addWidget(self.lbl_pos_z, 6, 2)

        thrust_layout = QHBoxLayout()
        main_layout.addLayout(thrust_layout)

        BAR_MAX_HEIGHT = 160

        self.pb_thrust = ThrustBar(
            label="T", tooltip="Thrust", label_center=True)
        self.pb_thrust.setMaximumHeight(BAR_MAX_HEIGHT)
        thrust_layout.addWidget(self.pb_thrust)

        self.pb_thrust_m1 = ThrustBar(
            label="M1", tooltip="Motor 1", label_center=True)
        self.pb_thrust_m1.setMaximumHeight(BAR_MAX_HEIGHT)
        thrust_layout.addWidget(self.pb_thrust_m1)

        self.pb_thrust_m2 = ThrustBar(
            label="M2", tooltip="Motor 2", label_center=True)
        self.pb_thrust_m2.setMaximumHeight(BAR_MAX_HEIGHT)
        thrust_layout.addWidget(self.pb_thrust_m2)

        self.pb_thrust_m3 = ThrustBar(
            label="M3", tooltip="Motor 3", label_center=True)
        self.pb_thrust_m3.setMaximumHeight(BAR_MAX_HEIGHT)
        thrust_layout.addWidget(self.pb_thrust_m3)

        self.pb_thrust_m4 = ThrustBar(
            label="M4", tooltip="Motor 4", label_center=True)
        self.pb_thrust_m4.setMaximumHeight(BAR_MAX_HEIGHT)
        thrust_layout.addWidget(self.pb_thrust_m4)

        self.left_layout.addWidget(self.gb_status)

    def _setup_btn_layout(self):
        layout = QVBoxLayout()

        connect_layout = QHBoxLayout()
        layout.addLayout(connect_layout)
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clicked.connect(self._connect_button_on_click)
        connect_layout.addWidget(self.btn_connect)

        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.clicked.connect(
            self._disconnect_button_on_click)
        connect_layout.addWidget(self.btn_disconnect)

        self.btn_arm = QPushButton("Arm")
        self.btn_arm.clicked.connect(self._arm_on_click)
        layout.addWidget(self.btn_arm)
        self.btn_arm.setEnabled(False)

        # Control group box
        self.gb_control = QGroupBox("Control")

        gb_main_layout = QGridLayout()
        self.gb_control.setLayout(gb_main_layout)
        layout.addWidget(self.gb_control)

        self.btn_take_off = QPushButton("Take Off")
        self.btn_take_off.clicked.connect(self._take_off_btn_on_click)
        gb_main_layout.addWidget(self.btn_take_off, 1, 1)

        self.btn_land = QPushButton("Land")
        self.btn_land.clicked.connect(self._land_btn_on_click)
        gb_main_layout.addWidget(self.btn_land, 2, 1)

        self.btn_move_forward = QPushButton()
        self.btn_move_forward.setIcon(Icon.get_icon(Icon.UP_ARROW))
        self.btn_move_forward.clicked.connect(
            lambda: self._fly_control_btn_on_click(FlyCommandManually.FORWARD))
        gb_main_layout.addWidget(self.btn_move_forward, 1, 3)

        self.btn_move_backward = QPushButton()
        self.btn_move_backward.setIcon(Icon.get_icon(Icon.DOWN_ARROW))
        self.btn_move_backward.clicked.connect(
            lambda: self._fly_control_btn_on_click(FlyCommandManually.BACKWARD))
        gb_main_layout.addWidget(self.btn_move_backward, 3, 3)

        self.btn_move_left = QPushButton()
        self.btn_move_left.setIcon(Icon.get_icon(Icon.LEFT_ARROW))
        self.btn_move_left.clicked.connect(
            lambda: self._fly_control_btn_on_click(FlyCommandManually.LEFT))
        gb_main_layout.addWidget(self.btn_move_left, 2, 2)

        self.btn_move_right = QPushButton()
        self.btn_move_right.setIcon(Icon.get_icon(Icon.RIGHT_ARROW))
        self.btn_move_right.clicked.connect(
            lambda: self._fly_control_btn_on_click(FlyCommandManually.RIGHT))
        gb_main_layout.addWidget(self.btn_move_right, 2, 4)

        self.btn_rotate_left = QPushButton()
        self.btn_rotate_left.setIcon(Icon.get_icon(Icon.TURN_DOWN_LEFT))
        self.btn_rotate_left.clicked.connect(
            lambda: self._fly_control_btn_on_click(FlyCommandManually.YAW_LEFT))
        self.btn_rotate_left.setToolTip("Rotate left")
        gb_main_layout.addWidget(self.btn_rotate_left, 1, 2)

        self.btn_rotate_right = QPushButton()
        self.btn_rotate_right.setIcon(Icon.get_icon(Icon.TURN_DOWN_RIGHT))
        self.btn_rotate_right.clicked.connect(
            lambda: self._fly_control_btn_on_click(FlyCommandManually.YAW_RIGHT))
        self.btn_rotate_right.setToolTip("Rotate right")
        gb_main_layout.addWidget(self.btn_rotate_right, 1, 4)

        self.btn_move_up = QPushButton("Up")
        self.btn_move_up.clicked.connect(
            lambda: self._fly_control_btn_on_click(FlyCommandManually.UP))
        gb_main_layout.addWidget(self.btn_move_up, 3, 1)

        self.btn_move_down = QPushButton("Down")
        self.btn_move_down.clicked.connect(
            lambda: self._fly_control_btn_on_click(FlyCommandManually.DOWN))
        gb_main_layout.addWidget(self.btn_move_down, 4, 1)

        self.btn_goto = QPushButton("")
        self.btn_goto.setToolTip("Go to")
        self.btn_goto.setIcon(Icon.get_icon(_Icon.GO_TO.value))
        self.btn_goto.clicked.connect(self._goto_btn_on_click)
        gb_main_layout.addWidget(self.btn_goto, 4, 2)

        self.btn_stop = QPushButton("")
        self.btn_stop.setToolTip("Stop and hover on current location")
        self.btn_stop.setIcon(Icon.get_icon(_Icon.STOP.value))
        self.btn_stop.clicked.connect(self._stop_btn_on_click)
        gb_main_layout.addWidget(self.btn_stop, 4, 4)

        self._fly_control_btn_setEnable(False)

        self.left_layout.addLayout(layout)

    @pyqtSlot(float)
    def _ui_link_quality_update(self, link_quality):
        """Update link quality 
        """
        if not self.is_showing:
            return
        if self._drone.is_connect:
            link_quality = round(link_quality / 10) * 10
            if link_quality > 80:
                color = PROGRESSBAR_GOOD_COLOR
            elif link_quality > 50:
                color = PROGRESSBAR_MEDIUM_COLOR
            else:
                color = PROGRESSBAR_BAD_COLOR
            self.pb_link_quality.setStyleSheet(
                f"{PROGRESSBAR_STYLE} QProgressBar::chunk {{background-color: {color};}}"
            )
            self.pb_link_quality.setValue(int(link_quality))
        else:
            self.pb_link_quality.setValue(0)

    @pyqtSlot(DroneInfo)
    def _ui_battery_callback(self, state: DroneInfo) -> None:
        """battery ui update callback

        Args:
            state (DroneState): state of drone
        """
        if not self.is_showing:
            return

        battery = int(state.battery_level)
        self.pb_battery_level.setValue(battery)
        if battery < 20:
            color = PROGRESSBAR_BAD_COLOR
        elif battery < 60:
            color = PROGRESSBAR_MEDIUM_COLOR
        else:
            color = PROGRESSBAR_GOOD_COLOR
        self.pb_battery_level.setStyleSheet(PROGRESSBAR_BATTERY % color)

        voltage = state.battery_voltage

        set_label_style_threshold(self.lbl_battery_voltage, voltage,
                                  CRITICAL_THRESHOLD["voltage_level"])

        self.lbl_battery_voltage.setText(f"{state.battery_voltage:.3f}V")

        self.lbl_battery_status.setText(
            get_battery_state_name(state.battery_state))

    @pyqtSlot(DroneInfo)
    def _ui_core_callback(self, state: DroneInfo) -> None:
        """core callback function

        Args:
            action (DroneUICallBack): action name
        """
        if not self.is_showing:
            return

        self.lbl_pitch.setText(f"{LABEL_PITCH} {state.pitch:.2f}")
        self.lbl_roll.setText(f"{LABEL_ROLL} {state.roll:.2f}")
        self.lbl_yaw.setText(f"{LABEL_YAW} {state.yaw:.2f}")

    @pyqtSlot(DroneInfo)
    def _ui_multi_ranger_callback(self, state: DroneInfo) -> None:
        """UI update for multi ranger

        Args:
            state (DroneState): _description_
        """
        if not self.is_showing:
            return

        self.lbl_front_distance.setText(
            f"{LABEL_FRONT_DISTANCE} {state.front_distance:.2f}")
        set_label_style_threshold(
            self.lbl_front_distance,
            state.front_distance,
            CRITICAL_THRESHOLD["front_distance"])

        self.lbl_back_distance.setText(
            f"{LABEL_BACK_DISTANCE} {state.rear_distance:.2f}")
        set_label_style_threshold(
            self.lbl_back_distance,
            state.rear_distance,
            CRITICAL_THRESHOLD["back_distance"])

        self.lbl_left_distance.setText(
            f"{LABEL_LEFT_DISTANCE} {state.left_distance:.2f}")
        set_label_style_threshold(
            self.lbl_left_distance,
            state.left_distance,
            CRITICAL_THRESHOLD["left_distance"])

        self.lbl_right_distance.setText(
            f"{LABEL_RIGHT_DISTANCE} {state.right_distance:.2f}")
        set_label_style_threshold(
            self.lbl_right_distance,
            state.right_distance,
            CRITICAL_THRESHOLD["right_distance"])

        self.lbl_height.setText(f"{LABEL_HEIGHT} {state.height:.2f}")

    @pyqtSlot(DroneInfo)
    def _ui_position_callback(self, state: DroneInfo) -> None:
        """UI update for position 
        """
        pos = state.position

        self.lbl_pos_x.setText(f"{LABEL_POS_X} {pos.x:.2f}")
        self.lbl_pos_y.setText(f"{LABEL_POS_Y} {pos.y:.2f}")
        self.lbl_pos_z.setText(f"{LABEL_POS_Z} {pos.z:.2f}")

    @pyqtSlot(DroneInfo)
    def _ui_motor_thrust_callback(self, state: DroneInfo) -> None:
        """UI update for motor thrust.
        """
        if not self.is_showing:
            return
        # if int(state.thrust) == 0 and self._drone.is_flying and not self._crash_warning_shown:
        #     self._crash_warning_shown = True
        #     logger.warning(f"{self._drone} might have been crashed.")
        self.pb_thrust.value = int(state.thrust)
        self.pb_thrust_m1.value = state.thrust_m1
        self.pb_thrust_m2.value = state.thrust_m2
        self.pb_thrust_m3.value = state.thrust_m3
        self.pb_thrust_m4.value = state.thrust_m4

    @pyqtSlot(FlyStatus)
    def _ui_drone_status_callback(self, status: FlyStatus):
        """ ui call back for updating drone status label
        """
        match status:
            case FlyStatus.LANDED:
                self.lbl_drone_status.icon_text = (
                    _Icon.LANDED.value, "Landed")
            case FlyStatus.LANDING:
                self.lbl_drone_status.icon_text = (
                    _Icon.LANDING.value, "Landing")
            case FlyStatus.TAKING_OFF:
                self.lbl_drone_status.icon_text = (
                    _Icon.TAKING_OFF.value, "Taking off")
            case FlyStatus.FLYING:
                self.lbl_drone_status.icon_text = (
                    _Icon.FLYING.value, "Flying")

    @pyqtSlot(DroneInfo)
    def _ui_loco_callback(self, status: DroneInfo):
        """ ui call back for updating loco deck mode
        """
        self.lbl_deck_loco_status.setToolTip(
            f"Loco Position ({get_loco_mode_name(status.loco_mode)})")

    def _reset(self):
        self._btn_reset()
        self._lbl_status_reset()
        self._lbl_decks_reset()
        self._thrust_reset()

    def _btn_reset(self):
        """Reset all the button to the beginning state. Only connect button is enabled. 
        """
        self.btn_take_off.setEnabled(False)
        self.btn_land.setEnabled(False)
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.btn_arm.setEnabled(False)

    def _thrust_reset(self):
        self.pb_thrust.value = 0
        self.pb_thrust_m1.value = 0
        self.pb_thrust_m2.value = 0
        self.pb_thrust_m3.value = 0
        self.pb_thrust_m4.value = 0

    def _lbl_status_reset(self):
        self.pb_battery_level.setValue(0)
        self.lbl_battery_voltage.setText("0.000 V")

        self.pb_link_quality.setValue(0)
        self.lbl_battery_status.setText("")
        self.lbl_front_distance.setText("Front: N/A")
        self.lbl_back_distance.setText("Back: N/A")
        self.lbl_left_distance.setText("Left: N/A")
        self.lbl_right_distance.setText("Right: N/A")
        self.lbl_height.setText("Height: N/A")
        self.lbl_pitch.setText("Pitch: N/A")
        self.lbl_roll.setText("Roll: N/A")
        self.lbl_yaw.setText("Yaw: N/A")
        self.lbl_pos_x.setText("X: N/A")
        self.lbl_pos_y.setText("Y: N/A")
        self.lbl_pos_z.setText("Z: N/A")

        set_label_style(self.lbl_battery_level, StylePreset.DEFAULT_TEXT)
        set_label_style(self.lbl_front_distance,
                        StylePreset.DEFAULT_TEXT)
        set_label_style(self.lbl_back_distance, StylePreset.DEFAULT_TEXT)
        set_label_style(self.lbl_left_distance, StylePreset.DEFAULT_TEXT)
        set_label_style(self.lbl_right_distance,
                        StylePreset.DEFAULT_TEXT)
        set_label_style(self.lbl_height, StylePreset.DEFAULT_TEXT)

    def _lbl_decks_reset(self):
        self.lbl_deck_z_flow_status.icon = _Icon.DISCONNECTED.value
        self.lbl_deck_loco_status.icon = _Icon.DISCONNECTED.value
        self.lbl_deck_loco_status.setToolTip("Loco Position")
        self.lbl_deck_multi_ranger_status.icon = _Icon.DISCONNECTED.value

    def _fly_control_btn_setEnable(self, enable: bool):
        self.btn_move_up.setEnabled(enable)
        self.btn_move_down.setEnabled(enable)
        self.btn_move_left.setEnabled(enable)
        self.btn_move_right.setEnabled(enable)
        self.btn_move_forward.setEnabled(enable)
        self.btn_move_backward.setEnabled(enable)
        self.btn_rotate_left.setEnabled(enable)
        self.btn_rotate_right.setEnabled(enable)

        self.btn_goto.setEnabled(enable)
        self.btn_stop.setEnabled(enable)

    def _btn_suc_connect(self):
        self.btn_take_off.setEnabled(False)
        self.btn_land.setEnabled(False)
        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)
        self.btn_arm.setEnabled(True)

    # Button On Click
    def _take_off_btn_on_click(self):
        try:
            self.btn_take_off.setEnabled(False)
            thread = Thread(target=self._drone.take_off)
            thread.start()
            self.btn_take_off.setEnabled(False)
            self.btn_land.setEnabled(True)
            self._fly_control_btn_setEnable(True)
        except DroneException as e:
            self.critical_msg_box("Drone Exception", str(e))

    def _land_btn_on_click(self):
        self._drone.land()
        self.btn_land.setEnabled(False)
        self.btn_take_off.setEnabled(True)
        self._fly_control_btn_setEnable(False)

    def _connect_button_on_click(self):
        """Connect button on click event
        """

        def connect_error(e: tuple) -> None:
            self.critical_msg_box("Drone Exception", str(e[1]))

        def connect_finish():
            if self._drone.is_connect:
                self.lbl_connection_status.icon_text = (
                    _Icon.CONNECTED.value, "Connected")

                drone_decks = self._drone.decks
                if drone_decks.z_flow:
                    self.lbl_deck_z_flow_status.icon = _Icon.CONNECTED.value
                if drone_decks.loco_position:
                    self.lbl_deck_loco_status.icon = _Icon.CONNECTED.value
                if drone_decks.multi_ranger:
                    self.lbl_deck_multi_ranger_status.icon = _Icon.CONNECTED.value
                self._btn_suc_connect()
            else:
                self.lbl_connection_status.icon_text = (
                    _Icon.DISCONNECTED.value, "Disconnected")
                self._btn_reset()

        def connect(**kwargs):
            self._drone.connect()

        self.lbl_connection_status.icon_text = (
            _Icon.CONNECTING.value, "Connecting")
        self.btn_connect.setEnabled(False)
        worker = Worker(connect)
        worker.signals.error.connect(connect_error)
        worker.signals.finished.connect(connect_finish)
        self._thread_pool.start(worker)

    def _disconnect_button_on_click(self):
        self.btn_disconnect.setEnabled(False)
        self.lbl_connection_status.icon_text = (
            _Icon.CONNECTING.value, "Disconnecting")
        thread = Thread(target=self._drone.disconnect)
        thread.start()
        self.lbl_connection_status.icon_text = (
            _Icon.DISCONNECTED.value, "Disconnected")
        thread.join()
        self._reset()

    def _fly_control_btn_on_click(self, command: FlyCommandManually):
        self._drone.fly_control.manually_fly(command)

    def _goto_btn_on_click(self):
        """Go to button on click function call
        """
        dialog = GoToDialog(self._drone, parent=self)
        value = dialog.exec()
        if value == QDialog.DialogCode.Accepted:
            desc = Position(dialog.position.x, dialog.position.y,
                            self._drone.state.position.z)
            self._drone.fly_control.go_to(desc)

    def _stop_btn_on_click(self):
        """Stop button on click function call
        """
        self._drone.fly_control.stop()

    def _arm_on_click(self):
        # Get the current arm state
        is_arm = self._drone.is_arm

        if not is_arm:
            self._drone.set_arm(True)
            LOGGER.debug('Setting arm to True')

        else:
            self._drone.set_arm(False)
            LOGGER.debug('Setting arm to False')

        # Ensure it is armed
        if self._drone.is_arm:
            self.btn_arm.setText("Disarm")
            self.btn_take_off.setEnabled(True)
        else:
            self.btn_arm.setText("Arm")
            self.btn_take_off.setEnabled(False)

    @pyqtSlot()
    def _connection_lost(self, *_):
        self.critical_msg_box("Drone Exception",
                              "Drone connection lost, please reconnect.")
        self.lbl_connection_status.icon_text = (
            _Icon.DISCONNECTED.value, "Disconnected")
        self.lbl_deck_z_flow_status.icon = _Icon.DISCONNECTED.value
        self.lbl_deck_loco_status.icon = _Icon.DISCONNECTED.value
        self.lbl_deck_multi_ranger_status.icon = _Icon.DISCONNECTED.value
        self._reset()

    def critical_msg_box(self, title: str, message: str):
        QMessageBox.critical(
            self, f"{title} ({self._drone.name})", message)

    def disconnect_stream(self):
        self.stream_widget.stop_stream()

    def set_is_showing(self, is_showing: bool):
        self._showing = is_showing
        self.stream_widget.set_visible(is_showing)


class _VideoStreamSignals(QObject):
    stream_started = pyqtSignal()
    connection_lost = pyqtSignal()
    stream_error = pyqtSignal(Exception)
    stream_ended = pyqtSignal()
    invalid_stream = pyqtSignal(str)


class VideoStream(QWidget):

    def __init__(self,
                 drone: Drone,
                 parent=None,
                 stream_resolution: tuple = (640, 480),
                 ):
        super().__init__(parent)
        self._drone = drone
        self._resolution = stream_resolution
        self._is_visible = False
        self._signals = _VideoStreamSignals()
        self._setup_ui()
        self._setup_callbacks()

    def _setup_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        gb = QGroupBox("Stream")
        main_layout.addWidget(gb)
        layout = QVBoxLayout()
        gb.setLayout(layout)

        self.lbl_stream_url = QLabel(self._drone.stream_url)
        self.lbl_stream_url.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.lbl_stream_url)

        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        self.btn_start = QPushButton("Start")
        self.btn_start.clicked.connect(self._stream_start)
        btn_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self._drone.stream_stop)
        self.btn_stop.setEnabled(False)
        btn_layout.addWidget(self.btn_stop)

        self.cb_object_detection = QCheckBox("Object Detection")
        self.cb_object_detection.setChecked(False)
        self.cb_object_detection.clicked.connect(
            lambda: self._drone.set_object_detection(self.cb_object_detection.isChecked()))
        btn_layout.addWidget(self.cb_object_detection)

        self.video = DroneStreamWidget(self._drone, self._resolution)
        layout.addWidget(self.video)

    def _stream_start(self):
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(False)
        thread = Thread(target=self._drone.stream_start)
        thread.start()

    def _setup_callbacks(self):
        self._drone.video_callbacks.stream_started.add_callback(
            self._signals.stream_started.emit)
        self._signals.stream_started.connect(self._stream_started)

        self._drone.video_callbacks.stream_error.add_callback(
            self._signals.stream_error.emit)
        self._signals.stream_error.connect(self._reset)

        self._drone.video_callbacks.stream_ended.add_callback(
            self._signals.stream_ended.emit)
        self._signals.stream_ended.connect(self._reset)

        self._drone.video_callbacks.invalid_stream.add_callback(
            self._signals.invalid_stream.emit)
        self._signals.invalid_stream.connect(self._reset)

        self._drone.video_callbacks.connection_lost.add_callback(
            self._signals.connection_lost.emit)
        self._signals.connection_lost.connect(self._reset)

    def _stream_started(self):
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def _reset(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def set_visible(self, value: bool) -> None:
        self._is_visible = value
        self.video.set_visible(value)

# https://www.pythonguis.com/tutorials/multithreading-pyqt6-applications-qthreadpool/


class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    '''
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value))
        else:
            # Return the result of the processing
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()  # Done
