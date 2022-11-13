from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

from general.enum import IntEnum
from general.utils import is_number, Position
from hub.location import LOCATIONS, Location
from ui.widget.utils import set_label_style, StylePreset


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

        self.location = Location(name=self.le_name.text() if self._show_name else "",
                                 position=self._get_position())

        super().accept()

    def _get_position(self):
        return Position(float(self.le_x.text()),
                        float(self.le_y.text()),
                        float(self.le_z.text()))
