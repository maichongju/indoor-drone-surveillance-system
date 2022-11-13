from PyQt6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QPushButton

from hub.location import LOCATIONS
from ui.icon import Icon
from ui.widget.dialog.locationeditdialog import LocationEditDialog
from ui.widget.list import LocationListWidget, LocationItem


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
