from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QLineEdit, QWidget

from general.enum import Enum
from general.utils import Axis, Position
from hub.drone import Drone
from hub.location import Location, LOCATIONS
from ui.icon import Icon
from ui.widget.dialog.locationeditdialog import LocationEditDialog
from ui.widget.list import LocationListWidget, LocationItem
from ui.widget.utils import set_label_style, StylePreset


class _Icon(Enum):
    CURRENT_LOCATION = Icon.DOWNLOAD


class GoToDialog(QDialog):
    """Dialog for go to a location.
    """

    def __init__(self, drone: Drone, parent=None):
        super().__init__(parent)
        self._drone = drone
        self.setWindowTitle("Go to location")
        self.position = None
        self._setup_ui()
        self.setFixedSize(self.sizeHint())

    def _setup_ui(self):

        layout = QVBoxLayout()
        self.setLayout(layout)

        center_layout = QHBoxLayout()
        layout.addLayout(center_layout)

        cord_layout = QVBoxLayout()
        center_layout.addLayout(cord_layout)

        cord_layout.addWidget(QLabel("Enter the destination location"))
        # location_layout = QHBoxLayout()
        # cord_layout.addLayout(location_layout)

        self.pos_x = PositionLabelEditSetWidget("X:", parent=self)
        self.pos_x.btn.clicked.connect(lambda: self._position_btn_click_callback(Axis.X))
        self.pos_x.btn.setToolTip("Get current X position")
        cord_layout.addWidget(self.pos_x)

        self.pos_y = PositionLabelEditSetWidget("Y:", parent=self)
        self.pos_y.btn.clicked.connect(lambda: self._position_btn_click_callback(Axis.Y))
        self.pos_y.btn.setToolTip("Get current Y position")
        cord_layout.addWidget(self.pos_y)

        self.pos_z = PositionLabelEditSetWidget("Z:", parent=self)
        self.pos_z.btn.clicked.connect(lambda: self._position_btn_click_callback(Axis.Z))
        self.pos_z.btn.setToolTip("Get current Z position")
        cord_layout.addWidget(self.pos_z)

        self.btn_add_to_list = QPushButton("Add")
        self.btn_add_to_list.clicked.connect(self._add_btn_click_callback)
        cord_layout.addWidget(self.btn_add_to_list)

        self.lbl_error = QLabel()
        set_label_style(self.lbl_error, StylePreset.WARNING_TEXT)
        cord_layout.addWidget(self.lbl_error)

        cord_layout.addStretch()

        # Layout for location list
        right_layout = QHBoxLayout()
        center_layout.addLayout(right_layout)

        self.location_list = LocationListWidget(self)
        right_layout.addWidget(self.location_list)

        self.location_list.setFixedSize(120, 150)
        self.location_list.itemDoubleClicked.connect(self._list_double_click_callback)

        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        btn_layout.addStretch()

        self.btn_ok = QPushButton("Go")
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

    def _list_double_click_callback(self, item: LocationItem):
        """Callback function for double click item

        Args:
            item (LocationItem): double clicked item
        """
        self.pos_x.le.setText(str(item.location.position.x))
        self.pos_y.le.setText(str(item.location.position.y))
        self.pos_z.le.setText(str(item.location.position.z))

    def _position_btn_click_callback(self, flag: Axis):
        """Position button callback function

        Args:
            flag (Position.Flag): Pos to modify
        """
        match flag:
            case Axis.X:
                self.pos_x.le.setText(str(self._drone.state.position.x))
            case Axis.Y:
                self.pos_y.le.setText(str(self._drone.state.position.y))
            case Axis.Z:
                self.pos_z.le.setText(str(self._drone.state.position.z))

    def _add_btn_click_callback(self):
        if (self._validate_input()):
            pos = Position(
                float(self.pos_x.le.text()),
                float(self.pos_y.le.text()),
                float(self.pos_z.le.text())
            )
            location = Location(position=pos)
            dialog = LocationEditDialog(location=location, parent=self, mode=LocationEditDialog.Mode.ADD)
            result = dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                self.location_list.addItem(dialog.location)

    def _validate_input(self) -> bool:
        """Check if the position is valid. `True` if valid. `False` otherwise.

        Returns:
            bool: `True` if valid. `False` otherwise.
        """
        try:
            float(self.pos_x.le.text())
            float(self.pos_y.le.text())
            float(self.pos_z.le.text())
            return True
        except ValueError:
            return False

    def accept(self):
        if self._validate_input():
            self.position = Position(
                float(self.pos_x.le.text()),
                float(self.pos_y.le.text()),
                float(self.pos_z.le.text())
            )
            LOCATIONS.save(new_location=self.location_list.locations)
            super().accept()
        else:
            self.lbl_error.setText("Invalid X or Y or Z position")


class PositionLabelEditSetWidget(QWidget):
    """Special group of widget for GoToDialog. It contain a label, line edit and
    a button
    """

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._setup_ui(label)

    def _setup_ui(self, label: str):
        layout = QHBoxLayout()

        self.setLayout(layout)

        layout.addWidget(QLabel(label))

        self.le = QLineEdit()
        self.le.setMaximumWidth(40)
        layout.addWidget(self.le)

        self.btn = QPushButton()
        self.btn.setIcon(Icon.get_icon(_Icon.CURRENT_LOCATION.value))
        layout.addWidget(self.btn)

        layout.addStretch()
