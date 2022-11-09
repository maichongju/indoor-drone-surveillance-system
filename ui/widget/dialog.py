from enum import Enum, IntEnum

from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QVBoxLayout)

from general.utils import Axis, Position, is_number
from hub.drone import Drone
from hub.location import LOCATIONS, Location
from ui.icon import Icon
from ui.widget.list import LocationItem, LocationListWidget
from ui.widget.utils import StylePreset, set_label_style
from ui.widget.widget import PositionLabelEditSetWidget


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


class LocationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.setFixedSize(self.sizeHint())

    def _setup_ui(self):

        self.setWindowIcon(Icon.get_icon(Icon.SETTING_WHEEL))
        self.setWindowTitle("Location Setting")

        layout = QHBoxLayout()
        self.setLayout(layout)

        self.locations_list = LocationListWidget(self)
        self.locations_list.setFixedSize(120, 180)
        self.locations_list.itemDoubleClicked.connect(self.show_edit_dialog)
        self.locations_list.itemClicked.connect(self._list_single_click)
        layout.addWidget(self.locations_list)

        btn_layout = QVBoxLayout()
        layout.addLayout(btn_layout)

        btn_add = QPushButton("Add")
        btn_add.clicked.connect(self._btn_add_onclick)
        btn_layout.addWidget(btn_add)

        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._btn_edit_onclick)
        btn_layout.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._btn_delete_onclick)
        btn_layout.addWidget(self.btn_delete)

        btn_layout.addStretch()

        btn_save = QPushButton("Save")
        btn_save.setToolTip("Save the current location list")
        btn_save.clicked.connect(self._btn_save_onclick)
        btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setToolTip("Discard all the changes")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

    def show_edit_dialog(self, item: LocationItem):
        old_location_name = item.location.name
        dialog = LocationEditDialog(location=item.location,
                                    parent=self)
        value = dialog.exec()
        if value == QDialog.DialogCode.Accepted:
            item.update()
            self.locations_list.locations.update_location(old_location_name, dialog.location.name,
                                                          dialog.location.position)

    def _list_single_click(self, item: LocationItem):
        self.btn_edit.setEnabled(True)
        self.btn_delete.setEnabled(True)

    def _btn_edit_onclick(self):
        self.show_edit_dialog(self.locations_list.currentItem())

    def _btn_delete_onclick(self):
        index = self.locations_list.currentRow()
        self.locations_list.remove(index)
        if self.locations_list.is_empty():
            self.btn_delete.setEnabled(False)
            self.btn_edit.setEnabled(False)

    def _btn_add_onclick(self):
        dialog = LocationEditDialog(parent=self, mode=LocationEditDialog.Mode.ADD)
        value = dialog.exec()
        if value == QDialog.DialogCode.Accepted:
            self.locations_list.addItem(dialog.location)

    def _btn_save_onclick(self):
        LOCATIONS.save(new_location=self.locations_list.locations)
        self.accept()


class LocationEditDialog(QDialog):
    class Mode(IntEnum):
        EDIT = 0,
        ADD = 1

    def __init__(self,
                 location: Location = None,
                 parent=None,
                 mode: Mode = Mode.EDIT,
                 show_name: bool = True):
        super().__init__(parent)
        self.location = location
        self._is_update = mode == self.Mode.EDIT
        self.setWindowTitle("Edit Location" if self._is_update else "Add Location")
        self._setup_ui(show_name)
        self._show_name = show_name
        self.setFixedSize(self.sizeHint())

    def _setup_ui(self, show_name):

        layout = QVBoxLayout()
        self.setLayout(layout)

        if show_name:
            name_layout = QHBoxLayout()
            layout.addLayout(name_layout)
            name_layout.addWidget(QLabel("Name:"))
            self.le_name = QLineEdit(self.location.name if self.location is not None else "")
            name_layout.addWidget(self.le_name)

        location_layout = QHBoxLayout()
        layout.addLayout(location_layout)

        location_layout.addWidget(QLabel("X:"))
        self.le_x = QLineEdit(str(self.location.position.x if self.location is not None else ""))
        self.le_x.setMaximumWidth(100)
        location_layout.addWidget(self.le_x)
        location_layout.addWidget(QLabel("Y:"))
        self.le_y = QLineEdit(str(self.location.position.y if self.location is not None else ""))
        self.le_y.setMaximumWidth(100)
        location_layout.addWidget(self.le_y)

        location_layout.addWidget(QLabel("Z:"))
        self.le_z = QLineEdit(str(self.location.position.z if self.location is not None else ""))
        self.le_z.setMaximumWidth(100)
        location_layout.addWidget(self.le_z)

        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        self.lbl_error = QLabel()
        set_label_style(self.lbl_error, StylePreset.WARNING_TEXT)
        btn_layout.addWidget(self.lbl_error)

        btn_layout.addStretch()
        btn_ok = QPushButton('Update' if self._is_update else 'Add')
        btn_ok.clicked.connect(self._btn_ok_on_click)
        btn_layout.addWidget(btn_ok)

        btn_cancel = QPushButton('Cancel')
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

    def _btn_ok_on_click(self):
        """Ensure the input is valid. No duplicate name can exist in the list.
        """

        # Check the name.
        if self._show_name:
            if self.le_name.text() == "":
                self.lbl_error.setText("Name cannot be empty")
                return
            # For Location use case
            if self._is_update:

                if self.le_name.text() != self.location.name:
                    if LOCATIONS.existed(self.le_name.text()):
                        self.lbl_error.setText("Name already existed")
                        return

            else:
                if LOCATIONS.existed(self.le_name.text()):
                    self.lbl_error.setText("Name already existed")
                    return

        if self.le_x.text() == "" or self.le_y.text() == "" or self.le_z.text() == "":
            self.lbl_error.setText("Position cannot be empty")
            return

        if not is_number(self.le_x.text()) or not is_number(self.le_y.text()) or not is_number(self.le_z.text()):
            self.lbl_error.setText("Position must be a number")
            return

        self.location = Location(name=self.le_name.text(),
                                 position=self._get_position())

        super().accept()

    def _get_position(self):
        return Position(float(self.le_x.text()),
                        float(self.le_y.text()),
                        float(self.le_z.text()))
    